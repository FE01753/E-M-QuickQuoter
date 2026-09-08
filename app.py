import streamlit as st
import json
import re
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="E&M 工程報價單結構化工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 工程報價單結構化工具")
st.write("上載 PDF 或相片，精準還原為工程 Breakdown 格式（Category, Description, Qty, Unit, Unit Price, Amount），全欄位獨立 Copy！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始解析工程項目", type="primary", use_container_width=True):
        with st.spinner("🤖 正在還原工程 Breakdown 結構..."):
            try:
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
                elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                    image = Image.open(uploaded_file)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
                        data={'apikey': 'helloworld', 'language': 'chs', 'isOverlayRequired': False}
                    )
                    res = response.json()
                    if res.get('ParsedResults'):
                        raw_text = res['ParsedResults'][0].get('ParsedText', '')
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

        if raw_text.strip():
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            parsed_items = []
            current_item = None
            
            # 過濾公司標頭雜訊
            header_blacklist = ["road", "kowloon", "bay", "tel", "fax", "報價單", "quotation", "ref", "日期", "date", "致", "attn"]
            
            for line in lines:
                line_lower = line.lower()
                if any(kw in line_lower for kw in header_blacklist) and not re.match(r'^\d{1,3}\s', line):
                    continue
                
                # 嚴格配對 Item 編號開頭
                item_start_match = re.match(r'^(?:item)?\s*(\d{1,3})\s*[\.\s]\s*(.*)', line, re.IGNORECASE)
                
                if item_start_match:
                    if current_item:
                        parsed_items.append(current_item)
                    
                    item_num = item_start_match.group(1)
                    content = item_start_match.group(2)
                    
                    # 預設智能分類判斷 (Category)
                    cat = "HVAC (Air conditioning)"
                    if any(w in content.lower() for w in ["fire", "fs", "消防", "sprinkler", "alarm"]):
                        cat = "FS (Fire services items)"
                    elif any(w in content.lower() for w in ["plumbing", "drainage", "水", "排水"]):
                        cat = "P&D (Plumbing & Drainage)"
                    
                    current_item = {
                        "item_no": item_num,
                        "category": cat,
                        "raw_line": content,
                        "description": content,
                        "qty": "1.00",
                        "unit": "lot",
                        "unit_price": "",
                        "amount": ""
                    }
                else:
                    if current_item:
                        current_item["description"] += "\n" + line  # 保留換行，像第二張圖咁清晰
                        current_item["raw_line"] += " " + line
            
            if current_item:
                parsed_items.append(current_item)
            
            # 提取數量、單位、單價、金額
            final_items = []
            for item in parsed_items:
                text = item["raw_line"]
                
                prices = re.findall(r'(?:HKD|HK\$|\$)?\s*([\d,]+\.\d{2})', text)
                qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(項|米|批|套|個|件|組|set|sets|pc|pcs|m|nos|lot)\b', text, re.IGNORECASE)
                
                qty = "1.00"
                unit = "lot"
                if qty_match:
                    qty = qty_match.group(1)
                    unit_raw = qty_match.group(2).lower()
                    if "米" in unit_raw or "m" in unit_raw: unit = "m"
                    elif "個" in unit_raw or "pcs" in unit_raw: unit = "pcs"
                    elif "套" in unit_raw: unit = "set"
                
                unit_price = ""
                amount = ""
                if len(prices) >= 2:
                    unit_price = prices[0]
                    amount = prices[1]
                elif len(prices) == 1:
                    amount = prices[0]
                    
                desc = text
                if qty_match:
                    desc = desc.replace(qty_match.group(0), "")
                for p in prices:
                    desc = desc.replace(p, "")
                
                desc = re.sub(r'(?:HKD|HK\$|\$)', '', desc)
                desc = re.sub(r'[\,\.]+$', '', desc).strip()
                desc = re.sub(r'\s+', ' ', desc)
                
                final_items.append({
                    "item_no": item["item_no"],
                    "category": item["category"],
                    "description": item["description"] if item["description"] else desc,
                    "qty": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "amount": amount
                })
            
            st.session_state['breakdown_items'] = final_items
            st.success(f"🎉 成功轉換為工程 Breakdown 格式，共 {len(final_items)} 項！")

# 顯示對應第二張圖專業表格風格嘅卡片
if 'breakdown_items' in st.session_state and st.session_state['breakdown_items']:
    st.markdown("---")
    st.subheader(f"📋 Breakdown Details 項目清單（共 {len(st.session_state['breakdown_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['breakdown_items']):
        # 標題列
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### Item {item['item_no']}")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_group_{idx}", use_container_width=True):
                st.toast(f"已複製 Item {item['item_no']} 全部欄位！", icon="✅")
        
        # Category 選擇欄
        st.markdown("**Category**")
        item['category'] = st.selectbox("", ["HVAC (Air conditioning)", "FS (Fire services items)", "P&D (Plumbing & Drainage)", "E&L (Electrical items)"], index=0, key=f"cat_{idx}", label_visibility="collapsed")
        
        # Description 描述欄 (連獨立 Copy 掣)
        st.markdown("**Description**")
        new_desc = st.text_area("", value=item['description'], height=90, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        if st.button("📋 複製 Description", key=f"c_desc_{idx}", use_container_width=True):
            st.toast(f"已複製 Item {item['item_no']} Description！", icon="✅")
            
        # Qty, Unit, Unit Price, Amount 打橫排開 (每格都有獨立 Copy 掣)
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown("**Qty**")
            item['qty'] = st.text_input("", value=item['qty'], key=f"qty_{idx}", label_visibility="collapsed")
            if st.button("📋 複製 Qty", key=f"c_qty_{idx}", use_container_width=True):
                st.toast("已複製 Qty！", icon="✅")
                
        with c2:
            st.markdown("**Unit**")
            item['unit'] = st.selectbox("", ["lot", "m", "pcs", "set", "nos"], index=0, key=f"unit_{idx}", label_visibility="collapsed")
            if st.button("📋 複製 Unit", key=f"c_unit_{idx}", use_container_width=True):
                st.toast("已複製 Unit！", icon="✅")
                
        with c3:
            st.markdown("**Unit Price (HKD)**")
            item['unit_price'] = st.text_input("", value=item['unit_price'], key=f"up_{idx}", placeholder="0.00", label_visibility="collapsed")
            if st.button("📋 複製單價", key=f"c_up_{idx}", use_container_width=True):
                st.toast("已複製單價！", icon="✅")
                
        with c4:
            st.markdown("**Amount (HKD)**")
            item['amount'] = st.text_input("", value=item['amount'], key=f"amt_{idx}", placeholder="0.00", label_visibility="collapsed")
            if st.button("📋 複製金額", key=f"c_amt_{idx}", use_container_width=True):
                st.toast("已複製金額！", icon="✅")
                
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['breakdown_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
