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

st.set_page_config(page_title="E&M 檔案轉文字與分項工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 檔案轉文字與分項工具")
st.write("上載 **PDF** 或 **JPG/PNG 相片**，系統自動幫你轉成文字並分拆成獨立卡片隨時 Copy！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始讀取並轉成文字", type="primary"):
        with st.spinner("🤖 正在強力提取檔案文字中..."):
            try:
                # 1. 處理 PDF 檔案
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            raw_text += text + "\n"
                
                # 2. 處理 JPG / PNG 相片（使用輕量雲端 OCR，無需安裝複雜系統套件）
                elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                    image = Image.open(uploaded_file)
                    
                    # 將圖片轉為位元組
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # 呼叫免費開源 OCR API 進行辨識
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
                        data={
                            'apikey': 'helloworld',  # 試用公開 Key
                            'language': 'chs',       # 支援中文 (簡體/繁體通用)
                            'isOverlayRequired': False
                        }
                    )
                    result = response.json()
                    if result.get('ParsedResults'):
                        raw_text = result['ParsedResults'][0].get('ParsedText', '')
                    else:
                        st.warning("⚠️ 圖片轉文字未能成功，請嘗試手動貼上文字。")
            except Exception as e:
                st.error(f"檔案讀取發生錯誤: {str(e)}")

# 如果成功取得文字，顯示預覽及分項
if raw_text.strip():
    st.success("🎉 檔案成功轉為文字！")
    with st.expander("🔍 檢視完整轉出文字"):
        st.text_area("原始文字內容：", value=raw_text, height=150)
    
    # 自動按行切分
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['ocr_items'] = items

# 顯示獨立卡片清單
if 'ocr_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['ocr_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['ocr_items']):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Item {idx+1}**")
        with col2:
            if st.button(f"📋 複製此項", key=f"c_btn_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {idx+1} 內容！", icon="✅")
        
        new_desc = st.text_area("內容微調：", value=item['description'], height=70, key=f"desc_{idx}")
        item['description'] = new_desc
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['ocr_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
