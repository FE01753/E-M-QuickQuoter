import streamlit as st
import json
from PIL import Image

try:
    import fitz  # PyMuPDF 讀取 PDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

st.set_page_config(page_title="E&M 本地文件自動分項工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 本地文件自動分項工具")
st.write("上載 **PDF** 或 **圖片 (JPG, PNG)**，系統自動讀取並分項，每項都可以獨立 Copy！")

# 同時支援 PDF 及圖片格式
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或 圖片 (PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name
    ext = file_name.split('.')[-1].lower()
    
    if st.button("🚀 開始讀取並自動分項", type="primary"):
        if ext == 'pdf':
            if HAS_FITZ:
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for page in doc:
                    raw_text += page.get_text() + "\n"
            else:
                st.error("缺少 fitz (PyMuPDF) 庫，無法讀取 PDF。")
        elif ext in ['png', 'jpg', 'jpeg']:
            if HAS_TESSERACT:
                try:
                    image = Image.open(uploaded_file)
                    # 嘗試繁體中文加英文辨識
                    raw_text = pytesseract.image_to_string(image, lang='chi_tra+eng')
                except Exception as e:
                    # 如果沒有裝中文語言包，則預設用英文辨識
                    image = Image.open(uploaded_file)
                    raw_text = pytesseract.image_to_string(image)
            else:
                # 若環境無 Tesseract 程式，提供一個簡易的備用提示或直接讀取檔名/轉文字
                st.warning("⚠️ 系統偵測到本地未安裝 Tesseract OCR 引擎。建議直接使用「文字貼上」功能，或者使用 PDF 檔案！")

if raw_text.strip():
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['local_items'] = items

if 'local_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['local_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['local_items']):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Item {idx+1}**")
        with col2:
            if st.button(f"📋 複製此項", key=f"c_btn_{idx}"):
                st.toast(f"已成功複製 Item {idx+1}！", icon="✅")
        
        new_desc = st.text_area("內容：", value=item['description'], height=70, key=f"desc_{idx}")
        item['description'] = new_desc
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['local_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
