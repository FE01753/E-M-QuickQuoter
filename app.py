import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單一體化文字還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單一體化文字還原工具")
st.write("上載 PDF 或相片，直接還原成一篇完整格式嘅文字，方便一筆過 Copy！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    raw_text = ""
    
    if st.button("🚀 開始還原完整文字", type="primary", use_container_width=True):
        with st.spinner("🤖 正在讀取並整理為完整格式..."):
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
                # 簡單清理多餘空白行，保持原有排版感覺
                cleaned_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                st.session_state['full_text_output'] = "\n".join(cleaned_lines)
                st.success("🎉 成功還原整篇文件文字！")

if 'full_text_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 還原後嘅完整格式文字")
    st.write("你可以直接在下方全選複製，或微調修改內容：")
    
    # 放大版 text_area，方便直接複製整篇
    st.text_area("完整文字內容", value=st.session_state['full_text_output'], height=350, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['full_text_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
