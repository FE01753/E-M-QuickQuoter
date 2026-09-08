import streamlit as st
import requests
import io
from PIL import Image

# 嘗試引入 pdf2image 庫將 PDF 轉成圖片
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

st.set_page_config(page_title="報價單純文字排版還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單純文字排版還原工具")
st.write("支援上載 **PDF** 或 **相片 (JPG, PNG)**，自動轉為無格仔、乾淨流暢嘅純文字排版！")

# 📂 允許同時上載 PDF 與圖片
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (PDF, JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

def process_image_to_text(img_bytes, filename="file.jpg"):
    """ 核心 OCR 處理器：精準還原座標並組裝為無格仔純文字 """
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={filename: img_bytes},
        data={'apikey': 'helloworld', 'language': 'chs', 'isOverlayRequired': True}
    )
    res = response.json()
    
    if res.get('ParsedResults') and res['ParsedResults'][0].get('TextOverlay'):
        lines_data = res['ParsedResults'][0]['TextOverlay']['Lines']
        rows = []
        for line in lines_data:
            words = line.get('Words', [])
            if not words: continue
            top_y = words[0]['Top']
            left_x = words[0]['Left']
            text_str = "".join([w['WordText'] for w in words])
            
            placed = False
            for row in rows:
                if abs(row['y'] - top_y) < 14:  # 14像素內歸納同一行
                    row['items'].append({'x': left_x, 'text': text_str})
                    placed = True
                    break
            if not placed:
                rows.append({'y': top_y, 'items': [{'x': left_x, 'text': text_str}]})
        
        # 按 Y 軸由上到下排序
        rows.sort(key=lambda r: r['y'])
        
        clean_lines = []
        seen_lines = set()
        
        for row in rows:
            # 按照 X 軸由左到右排序
            row['items'].sort(key=lambda i: i['x'])
            
            row_texts = []
            for item in row['items']:
                t = item['text'].strip()
                if t and t not in row_texts:
                    row_texts.append(t)
            
            full_line = "   ".join(row_texts)
            
            if full_line in seen_lines:
                continue
            seen_lines.add(full_line)
            
            if full_line:
                clean_lines.append(full_line)
                
        return "\n".join(clean_lines)
    else:
        return res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原純文字格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在強力提取並轉化為無格仔純文字..."):
            try:
                raw_text = ""
                file_bytes = uploaded_file.read()
                
                # 💡 如果上載的是 PDF 檔案
                if file_name.endswith('.pdf'):
                    if HAS_PDF2IMAGE:
                        # 自動將 PDF 轉為圖片清單
                        images = convert_from_bytes(file_bytes)
                        page_texts = []
                        for idx, img in enumerate(images):
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='JPEG')
                            page_text = process_image_to_text(img_byte_arr.getvalue(), f"page_{idx}.jpg")
                            page_texts.append(page_text)
                        raw_text = "\n\n".join(page_texts)
                    else:
                        raw_text = "系統缺少 pdf2image 套件，暫時無法直接解析 PDF。請將 PDF 截圖成圖片上載即可。"
                
                # 💡 如果上載的是圖片格式 (JPG, PNG)
                else:
                    image = Image.open(io.BytesIO(file_bytes))
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    raw_text = process_image_to_text(img_byte_arr.getvalue(), uploaded_file.name)
                
                st.session_state['plain_text_output'] = raw_text
                st.success("🎉 純文字排版還原成功！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'plain_text_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 純文字排版預覽（無任何表格格仔）")
    st.text(st.session_state['plain_text_output'])
    
    st.markdown("### 📝 原始純文字（方便複製）")
    st.text_area("純文字內容", value=st.session_state['plain_text_output'], height=450, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['plain_text_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
