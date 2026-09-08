import streamlit as st
import json
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="E&M 報價單精準整理工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單精準整理工具")
st.write("上載 PDF 或相片，安全讀取每一行工程內容，讓你輕鬆逐項整理與複製！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始讀取報價單", type="primary", use_container_width=True):
        with st.spinner("🤖 正在提取文件內容..."):
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
            # 過濾空白或過短嘅行
            lines = [l.strip() for l in raw_text.split('\n') if len(l.strip()) > 3]
            
            # 過濾常見嘅頁首頁尾雜訊
            filtered_lines = []
            ignore_list = ["項目 item", "descriptions", "數量 qty", "單價", "金額 price", "page"]
            for line in lines:
                if not any(ign in line.lower() for ign in ignore_list):
                    filtered_lines.append(line)
            
            items = []
            for i, line in enumerate(filtered_lines):
                items.append({
                    "item_no": i + 1,
                    "description": line,
                    "qty": "",
                    "unit_price": "",
                    "amount": ""
                })
            st.session_state['clean_items'] = items
            st.success(f"🎉 成功讀取有效項目共 {len(items)} 個！")

# 顯示乾淨嘅卡片，讓你可以隨手執位
if 'clean_items' in st.session_state and st.session_state['clean_items']:
    st.markdown("---")
    st.subheader(f"📋 項目檢視與執位（共 {len(st.session_state['clean_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['clean_items']):
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**Item {idx+1}**")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_all_{idx}", use_container_width=True):
                st.toast(f"已複製 Item {idx+1}！", icon="✅")
        
        # 內容描述
        st.markdown("**內容 Descriptions**")
        new_desc = st.text_area("", value=item['description'], height=65, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        # 打橫一組：數量、單價、金額
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
        del st.session_state['clean_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
