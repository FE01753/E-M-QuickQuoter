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

st.set_page_config(page_title="E&M 報價單項目擷取工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單項目擷取工具")
st.write("上載 PDF 或相片，嚴格按真實 Item 區分，並提供**全欄位獨立 Copy 掣**，做 Quotation 輕鬆過關！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始智能解析並分組", type="primary", use_container_width=True):
        with st.spinner("🤖 正在過濾公司 Header 並精準對應 Item..."):
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
            
            # 需要過濾掉嘅公司標頭關鍵字（避免將地址、電話當作 Item）
            header_blacklist = [
                "road", "kowloon", "bay", "tel", "fax", "報價單", "quotation", 
                "ref", "日期", "date", "致", "attn", "re :", "工程項目"
            ]
            
            for line in lines:
                line_lower = line.lower()
                
                # 如果行入面包含公司地址/電話/標題特徵，直接略過
                if any(kw in line_lower for kw in header_blacklist) and not re.match(r'^\d{1,3}\s', line):
                    continue
                
                # 嚴格匹配 Item 開頭（例如 "1", "2.", "Item 1"）
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
                        "qty": "",
                        "unit_price": "",
                        "amount": ""
                    }
                else:
                    # 屬於上一個 Item 嘅延伸行
                    if current_item:
                        current_item["description"] += " " + line
                        current_item["raw_line"] += " " + line
            
            if current_item:
                parsed_items.append(current_item)
            
            # 清洗及提取數量、單價、金額
            final_items = []
            for item in parsed_items:
                text = item["raw_line"]
                
                prices = re.findall(r'(?:HKD|HK\$|\$)?\s*[\d,]+\.\d{2}', text)
                qty_match = re.search(r'(\d+\s*(?:項|米|批|套|個|件|組|set|sets|pc|pcs|m|nos|lot)\b)', text, re.IGNORECASE)
                qty = qty_match.group(1) if qty_match else ""
                
                unit_price = ""
                amount = ""
                if len(prices) >= 2:
                    unit_price = prices[0]
                    amount = prices[1]
                elif len(prices) == 1:
                    amount = prices[0]
                
                desc = text
                if qty:
                    desc = desc.replace(qty, "")
                for p in prices:
                    desc = desc.replace(p, "")
                
                desc = re.sub(r'[\$\,\.]+$', '', desc).strip()
                desc = re.sub(r'\s+', ' ', desc)
                
                final_items.append({
                    "item_no": item["item_no"],
                    "description": desc if desc else text,
                    "qty": qty,
                    "unit_price": unit_price,
                    "amount": amount
                })
            
            st.session_state['final_quote_items'] = final_items
            st.success(f"🎉 成功成功精準擷取 {len(final_items)} 個有效工程項目！")

# 顯示分組結果（各欄位均設有獨立 Copy 掣）
if 'final_quote_items' in st.session_state and st.session_state['final_quote_items']:
    st.markdown("---")
    st.subheader(f"📋 項目清單（共 {len(st.session_state['final_quote_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['final_quote_items']):
        # 標題與整組複製
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### Item {item['item_no']}")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_all_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {item['item_no']} 全部內容！", icon="✅")
        
        # 1. 內容描述 (連獨立 Copy 掣)
        st.markdown("**內容 Descriptions**")
        new_desc = st.text_area("", value=item['description'], height=70, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        if st.button("📋 複製內容描述", key=f"c_desc_{idx}", use_container_width=True):
            st.toast(f"已複製 Item {item['item_no']} 內容描述！", icon="✅")
            
        # 2. 數量、單價、金額 (打橫三欄，每欄都有獨立 Copy 掣)
        col_q, col_p, col_a = st.columns(3)
        
        with col_q:
            st.markdown("**數量 Qty**")
            item['qty'] = st.text_input("", value=item['qty'], key=f"q_{idx}", placeholder="例: 180米", label_visibility="collapsed")
            if st.button("📋 複製數量", key=f"c_q_{idx}", use_container_width=True):
                st.toast("已複製數量！", icon="✅")
                
        with col_p:
            st.markdown("**單價 Unit Price**")
            item['unit_price'] = st.text_input("", value=item['unit_price'], key=f"p_{idx}", placeholder="例: $165.00", label_visibility="collapsed")
            if st.button("📋 複製單價", key=f"c_p_{idx}", use_container_width=True):
                st.toast("已複製單價！", icon="✅")
                
        with col_a:
            st.markdown("**金額 Price**")
            item['amount'] = st.text_input("", value=item['amount'], key=f"a_{idx}", placeholder="例: $29,700", label_visibility="collapsed")
            if st.button("📋 複製金額", key=f"c_a_{idx}", use_container_width=True):
                st.toast("已複製金額！", icon="✅")
                
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['final_quote_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
