import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單純文字排版還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單純文字排版還原工具")
st.write("上載 PDF 或相片，直接轉為無格仔、乾淨流暢嘅純文字排版！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原純文字格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在提取並轉化為無格仔純文字..."):
            try:
                raw_text = ""
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: raw_text += t + "\n"
                else:
                    image = Image.open(uploaded_file)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
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
                            
                            # 去除重覆行
                            if full_line in seen_lines:
                                continue
                            seen_lines.add(full_line)
                            
                            if full_line:
                                clean_lines.append(full_line)
                                
                        raw_text = "\n".join(clean_lines)
                    else:
                        raw_text = res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')
                
                st.session_state['plain_text_output'] = raw_text
                st.success("🎉 純文字排版還原成功！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'plain_text_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 純文字排版預覽（無任何表格格仔）")
    st.write("以下為無格仔嘅流暢文字，你可以直接檢視或在下方複製：")
    
    # 直接用 markdown 顯示段落，完全唔會變左表格
    st.text(st.session_state['plain_text_output'])
    
    st.markdown("### 📝 原始純文字（方便複製）")
    st.text_area("純文字內容", value=st.session_state['plain_text_output'], height=450, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['plain_text_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
