import streamlit as st
import json
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

st.set_page_config(page_title="E&M 檔案自動 Scan 字工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 檔案自動 Scan 字工具")
st.write("直接上載 **PDF** 或 **JPG/PNG 相片**，系統自動轉成文字並分拆成獨立卡片隨時 Copy！")

uploaded_file = st.file_uploader("📂 請上載 PDF 或 圖片 (PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name
    ext = file_name.split('.')[-1].lower()
    
    if st.button("🚀 開始讀取並自動分項", type="primary"):
        with st.spinner("🤖 正在強力提取檔案文字中..."):
            try:
                if ext == 'pdf':
                    if HAS_PDF:
                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                raw_text += text + "\n"
                    else:
                        st.error("系統缺少 pypdf 套件。")
                elif ext in ['png', 'jpg', 'jpeg']:
                    if HAS_OCR:
                        image = Image.open(uploaded_file)
                        try:
                            # 優先嘗試繁體中文加英文辨識
                            raw_text = pytesseract.image_to_string(image, lang='chi_tra+eng')
                        except:
                            raw_text = pytesseract.image_to_string(image)
                    else:
                        st.warning("本地未安裝 Tesseract OCR 引擎。")
            except Exception as e:
                st.error(f"讀取檔案出錯: {str(e)}")

if raw_text.strip():
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['scanned_items'] = items
    st.success(f"🎉 成功自動 Scan 出 {len(items)} 個項目！")

if 'scanned_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['scanned_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['scanned_items']):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Item {idx+1}**")
        with col2:
            if st.button(f"📋 複製此項", key=f"c_btn_{idx}"):
                st.toast(f"已成功複製 Item {idx+1}！", icon="✅")
        
        new_desc = st.text_area("內容描述：", value=item['description'], height=70, key=f"desc_{idx}")
        item['description'] = new_desc
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['scanned_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
