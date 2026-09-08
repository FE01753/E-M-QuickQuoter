import streamlit as st
import json

# 嘗試載入圖片處理與本地 OCR 套件
try:
    from PIL import Image
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import fitz  # PyMuPDF 讀取 PDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 本地萬能文件/圖片 Scan 認字工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 本地文件/圖片 Scan 認字工具")
st.write("上載 PDF 或圖片，系統會直接在本地 Scan 認字，一秒轉成文字隨時 Copy！")

uploaded_file = st.file_uploader("📂 上載檔案 (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

scanned_text = ""

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if st.button("🚀 開始本地 Scan 認字", type="primary"):
        with st.spinner("正在進行本地 OCR 掃描中..."):
            extracted_lines = []
            
            # 1. 如果係圖片 (PNG / JPG)
            if file_extension in ['png', 'jpg', 'jpeg']:
                if HAS_TESSERACT:
                    try:
                        image = Image.open(uploaded_file)
                        # 支援中英文辨識
                        scanned_text = pytesseract.image_to_string(image, lang='chi_tra+eng')
                    except Exception as e:
                        scanned_text = f"OCR 掃描出錯: {str(e)} (請確保伺服器已安裝 tesseract-ocr)"
                else:
                    scanned_text = "⚠️ 伺服器未安裝 pytesseract，請使用文字直接貼上功能。"
            
            # 2. 如果係 PDF
            elif file_extension == 'pdf':
                if HAS_FITZ:
                    try:
                        import io
                        doc = fitz.open(stream=file_bytes, filetype="pdf")
                        for page in doc:
                            extracted_lines.append(page.get_text())
                        scanned_text = "\n".join(extracted_lines)
                    except Exception as e:
                        scanned_text = f"PDF 讀取出錯: {str(e)}"
                else:
                    scanned_text = "⚠️ 伺服器未安裝 PyMuPDF (fitz)。"
            
            st.session_state['scanned_result'] = scanned_text

if 'scanned_result' in st.session_state:
    st.markdown("---")
    st.subheader("📋 Scan 出嚟嘅文字結果")
    
    # 提供一個大文字框，方便用戶直接編輯或一鍵全選複製
    final_text = st.text_area(
        "你可以直接在下方修改或完整複製文字：",
        value=st.session_state['scanned_result'],
        height=250
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 複製全部文字"):
            st.toast("已成功讀取文字！", icon="✅")
    with col2:
        if st.button("🗑️ 清空重置"):
            del st.session_state['scanned_result']
            st.rerun()

st.markdown("<div style='text-align: center; color: #555555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
