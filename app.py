import streamlit as st
import json
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="E&M 全能文件自動分項工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 全能文件自動分項工具")
st.write("一個 App 搞掂：支援 **PDF 檔案**、**JPG/PNG 相片** 或 **直接貼上文字**！")

# 選擇模式
input_mode = st.radio("選擇輸入方式：", ["📂 上載檔案 (PDF / JPG / PNG)", "📝 直接貼上文字"], horizontal=True)

raw_text = ""

if "📂 上載檔案" in input_mode:
    uploaded_file = st.file_uploader("請上載報價單 PDF 或相片", type=["pdf", "png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        file_name = uploaded_file.name.lower()
        
        if st.button("🚀 開始讀取並自動分項", type="primary"):
            with st.spinner("🤖 正在強力提取檔案內容中..."):
                try:
                    if file_name.endswith('.pdf'):
                        if HAS_PDF:
                            reader = PdfReader(uploaded_file)
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    raw_text += text + "\n"
                    elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                        # 針對 JPG 圖片的處理提示
                        image = Image.open(uploaded_file)
                        st.image(image, caption="已上載的相片", use_container_width=True)
                        st.info("💡 提示：如果相片中係手寫或列印文字，你可以順便用下方嘅文字框微調補充，或者直接貼上文字最快！")
                        # 這裡可以加入基本的圖片說明文字
                        raw_text = f"[已上載圖片: {uploaded_file.name}] 請在下方確認或補充內容文字。"
                except Exception as e:
                    st.error(f"讀取檔案出錯: {str(e)}")
else:
    raw_text = st.text_area("請在此貼上報價單內容：", height=140, placeholder="1. 供應及安裝 AFA 報警面板\n2. 檢查低壓配電箱")
    if st.button("🚀 開始自動分項", type="primary"):
        pass

if raw_text.strip():
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['all_items'] = items
    st.success(f"🎉 成功拆分出 {len(items)} 個項目！")

if 'all_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['all_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['all_items']):
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
        del st.session_state['all_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
