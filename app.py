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

st.set_page_config(page_title="E&M 報價單文字直接還原工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單文字直接還原工具")
st.write("上載 PDF 或相片，直接將每一句工程內容還原為純文字，各欄位全配獨立 Copy 掣！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始直接還原文字", type="primary", use_container_width=True):
        with st.spinner("🤖 正在直接讀取並轉化為文字..."):
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
                    
                    current_item = {
                        "item_no": item_num,
                        "raw_line": content,
                        "description": content,
                        "qty": "1.00 lot",
                        "unit_price": "",
                        "amount": ""
                    }
                else:
                    if current_item:
                        current_item["description"] += " " + line  # 直接變順暢嘅文字句子
                        current_item["raw_line"] += " " + line
            
            if current_item:
                parsed_items.append(current_item)
            
            # 提取數量、單價、金額
            final_items = []
            for item in parsed_items:
                text = item["raw_line"]
                
                prices = re.findall(r'(?:HKD|HK\$|\$)?\s*([\d,]+\.\d{2})', text)
                qty_match = re.search(r'(\d+(?:\.\d+)?\s*(?:項|米|批|套|個|件|組|set|sets|pc|pcs|m|nos|lot)\b)', text, re.IGNORECASE)
                
                qty = "1.00 lot"
                if qty_match:
                    qty = qty_match.group(1)
                
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
                    "description": item["description"] if item["description"] else desc,
                    "qty": qty,
                    "unit_price": unit_price,
                    "amount": amount
                })
            
            st.session_state['pure_text_items'] = final_items
            st.success(f"🎉 成功還原為純文字項目，共 {len(final_items)} 項！")

# 顯示純文字清單卡片
if 'pure_text_items' in st.session_state and st.session_state['pure_text_items']:
    st.markdown("---")
    st.subheader(f"📋 純文字項目清單（共 {len(st.session_state['pure_text_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['pure_text_items']):
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### Item {item['item_no']}")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_group_{idx}", use_container_width=True):
                st.toast(f"已複製 Item {item['item_no']} 全部！", icon="✅")
        
        # 內容描述 (純文字句子)
        st.markdown("**Descriptions (純文字)**")
        new_desc = st.text_area("", value=item['description'], height=90, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        if st.button("📋 複製 Descriptions", key=f"c_desc_{idx}", use_container_width=True):
            st.toast(f"已複製 Item {item['item_no']} 描述！", icon="✅")
            
        # 數量、單價、金額 打橫排開
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**Qty / 數量**")
            item['qty'] = st.text_input("", value=item['qty'], key=f"qty_{idx}", label_visibility="collapsed")
            if st.button("📋 複製數量", key=f"c_qty_{idx}", use_container_width=True):
                st.toast("已複製數量！", icon="✅")
                
        with c2:
            st.markdown("**Unit Price / 單價**")
            item['unit_price'] = st.text_input("", value=item['unit_price'], key=f"up_{idx}", placeholder="0.00", label_visibility="collapsed")
            if st.button("📋 複製單價", key=f"c_up_{idx}", use_container_width=True):
                st.toast("已複製單價！", icon="✅")
                
        with c3:
            st.markdown("**Amount / 金額**")
            item['amount'] = st.text_input("", value=item['amount'], key=f"amt_{idx}", placeholder="0.00", label_visibility="collapsed")
            if st.button("📋 複製金額", key=f"c_amt_{idx}", use_container_width=True):
                st.toast("已複製金額！", icon="✅")
                
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['pure_text_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
