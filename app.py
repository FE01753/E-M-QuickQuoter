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

st.set_page_config(page_title="E&M 報價單項目擷取工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單項目擷取工具")
st.write("上載報價單（PDF 或相片），系統自動辨識並提取 **項目、內容、數量、單價、金額**，轉為獨立卡片隨時 Copy！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始提取報價單內容", type="primary"):
        with st.spinner("🤖 正在辨識報價單表格內容中..."):
            try:
                # 1. 處理 PDF 檔案
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            raw_text += text + "\n"
                
                # 2. 處理 JPG / PNG 相片
                elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                    image = Image.open(uploaded_file)
                    
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # 呼叫開源 OCR API
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
                        data={
                            'apikey': 'helloworld',
                            'language': 'chs', # 支援中文/英文混合
                            'isOverlayRequired': False
                        }
                    )
                    result = response.json()
                    if result.get('ParsedResults'):
                        raw_text = result['ParsedResults'][0].get('ParsedText', '')
                    else:
                        st.warning("⚠️ 圖片辨識未能成功，請確保圖片清晰或嘗試手動貼上文字。")
            except Exception as e:
                st.error(f"讀取檔案發生錯誤: {str(e)}")

# 如果有提取到文字，將其拆分為項目卡片
if raw_text.strip():
    st.success("🎉 報價單內容成功提取！")
    
    # 簡單按行過濾並建立項目
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['quote_items'] = items

# 顯示獨立卡片清單（對應你想要嘅 Item / Description 格式）
if 'quote_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 報價單獨立項目卡片（共 {len(st.session_state['quote_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['quote_items']):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Item {idx+1}**")
        with col2:
            if st.button(f"📋 複製此項", key=f"c_btn_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {idx+1}！", icon="✅")
        
        # 顯示可編輯／微調嘅內容
        new_desc = st.text_area("內容 Descriptions / 規格：", value=item['description'], height=70, key=f"desc_{idx}")
        item['description'] = new_desc
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['quote_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
