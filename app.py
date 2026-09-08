import streamlit as st
import json

try:
    import fitz  # PyMuPDF 讀取 PDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 文件自動分項工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 文件自動分項工具")
st.write("支援 **PDF 檔案上載** 或 **直接貼上文字**，系統秒速自動分項，每項都可以獨立 Copy！")

input_mode = st.radio("選擇輸入方式：", ["📂 上載 PDF 檔案", "📝 直接貼上文字"], horizontal=True)

raw_text = ""

if "📂 上載 PDF 檔案" in input_mode:
    uploaded_pdf = st.file_uploader("請上載報價單 PDF", type=["pdf"])
    if uploaded_pdf is not None and HAS_FITZ:
        if st.button("🚀 開始讀取 PDF 並分項", type="primary"):
            doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
            for page in doc:
                raw_text += page.get_text() + "\n"
else:
    raw_text = st.text_area("請在此貼上報價單內容：", height=120)
    if st.button("🚀 開始自動分項", type="primary"):
        pass

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
