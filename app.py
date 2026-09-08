import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單單行流暢還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單單行流暢還原工具")
st.write("上載 PDF 或相片，自動將散亂碎字合併，確保每個 Item 一行過顯示！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始整合為單行格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在智能合併碎行與金額..."):
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
                        
                        extracted_lines = []
                        seen_lines = set()
                        
                        for row in rows:
                            row['items'].sort(key=lambda i: i['x'])
                            row_texts = []
                            for item in row['items']:
                                t = item['text'].strip()
                                if t and t not in row_texts:
                                    row_texts.append(t)
                            
                            full_line = " ".join(row_texts)
                            
                            # 濾走重複空白或重覆行
                            if full_line in seen_lines:
                                continue
                            seen_lines.add(full_line)
                            
                            if full_line:
                                extracted_lines.append(full_line)
                        
                        # 💡 核心智慧合併：如果下一行係金額 (HK$)、尺寸規格 (mm) 或獨立細節，自動黏埋落上一行
                        merged_lines = []
                        for line in extracted_lines:
                            # 判斷當前行是否屬於「需要貼返上去上一行」嘅碎字
                            is_fragment = (
                                line.startswith("HK$") or 
                                line.startswith("100mm") or 
                                line.startswith("25mm") or
                                ("喉" in line and len(line) < 35)
                            )
                            
                            if merged_lines and is_fragment:
                                # 拼埋落上一行，中間加個空格或逗號
                                merged_lines[-1] = f"{merged_lines[-1]}   {line}"
                            else:
                                merged_lines.append(line)
                                
                        raw_text = "\n\n".join(merged_lines)
                    else:
                        raw_text = res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')
                
                st.session_state['single_line_output'] = raw_text
                st.success("🎉 單行整合成功！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'single_line_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 單行流暢文本預覽")
    st.write("所有碎行同金額已經自動黏返埋同一行，眼不花：")
    
    st.text(st.session_state['single_line_output'])
    
    st.markdown("### 📝 最終純文字（可直接複製）")
    st.text_area("單行文本", value=st.session_state['single_line_output'], height=450, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['single_line_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
