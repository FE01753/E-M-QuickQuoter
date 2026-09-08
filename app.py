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

st.set_page_config(page_title="E&M 報價單精準對齊工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單精準對齊工具")
st.write("上載 PDF 或相片，完美對應香港 E&M 報價單格式，將內容、數量、單價、金額精準歸位！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始智能解析報價單", type="primary", use_container_width=True):
        with st.spinner("🤖 正在還原報價單橫向表格結構..."):
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
            
            ignore_keywords = ["項目 item", "descriptions", "數量 qty", "單價", "金額 price", "page"]
            
            for line in lines:
                if any(ign in line.lower() for ign in ignore_keywords) and len(line) < 15:
                    continue
                
                # 嘗試精準尋找金額 (例如 HK$6,000.00 或 $6,000)
                prices = re.findall(r'(?:HKD|HK\$|\$)?\s*[\d,]+\.\d{2}', line)
                
                # 嘗試尋找數量 (例如 1項, 180米, 2 sets)
                qty_match = re.search(r'(\d+\s*(?:項|米|批|套|個|件|組|set|sets|pc|pcs|m|nos|lot)\b)', line, re.IGNORECASE)
                qty = qty_match.group(1) if qty_match else ""
                
                unit_price = ""
                amount = ""
                if len(prices) >= 2:
                    unit_price = prices[0]
                    amount = prices[1]
                elif len(prices) == 1:
                    amount = prices[0]
                
                # 剝離數量同金額，保留真正的文字 Description
                desc = line
                if qty:
                    desc = desc.replace(qty, "")
                for p in prices:
                    desc = desc.replace(p, "")
                
                # 清理多餘符號
                desc = re.sub(r'[\$\,\.]+$', '', desc).strip()
                desc = re.sub(r'\s+', ' ', desc)
                
                # 如果描述太短或者只剩數字，就直接保留整行做 Description，避免變成亂碼 "HK"
                if len(desc) < 3:
                    desc = line
                
                parsed_items.append({
                    "item_no": len(parsed_items) + 1,
                    "description": desc,
                    "qty": qty if qty else "",
                    "unit_price": unit_price if unit_price else "",
                    "amount": amount if amount else ""
                })
                
            st.session_state['parsed_items'] = parsed_items
            st.success(f"🎉 成功解析全部 {len(parsed_items)} 個項目！")

# 顯示完美對齊截圖排版的介面
if 'parsed_items' in st.session_state and st.session_state['parsed_items']:
    st.markdown("---")
    st.subheader(f"📋 報價單解析結果（共 {len(st.session_state['parsed_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['parsed_items']):
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**Item {idx+1}**")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_group_{idx}", use_container_width=True):
                st.toast(f"已複製 Item {idx+1}！", icon="✅")
        
        st.markdown("**內容 Descriptions**")
        new_desc = st.text_area("", value=item['description'], height=75, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        # 下方打橫一組：數量、單價、金額
        col_q, col_p, col_a = st.columns(3)
        with col_q:
            st.markdown("**數量 Qty**")
            item['qty'] = st.text_input("", value=item['qty'], key=f"q_{idx}", placeholder="例如: 180米", label_visibility="collapsed")
        with col_p:
            st.markdown("**單價 Unit Price**")
            item['unit_price'] = st.text_input("", value=item['unit_price'], key=f"p_{idx}", placeholder="例如: $165.00", label_visibility="collapsed")
        with col_a:
            st.markdown("**金額 Price**")
            item['amount'] = st.text_input("", value=item['amount'], key=f"a_{idx}", placeholder="例如: $29,700", label_visibility="collapsed")
            
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['parsed_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
