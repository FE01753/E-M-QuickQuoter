import streamlit as st
import requests
import io
import re
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單乾淨文字還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單乾淨文字還原工具")
st.write("上載 PDF 或相片，自動去除重複並重組為乾淨易讀嘅報價單文字格式！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原乾淨格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在過濾重複並重組排版..."):
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
                                if abs(row['y'] - top_y) < 14:  # 稍微放寬至14像素歸納同一行
                                    row['items'].append({'x': left_x, 'text': text_str})
                                    placed = True
                                    break
                            if not placed:
                                rows.append({'y': top_y, 'items': [{'x': left_x, 'text': text_str}]})
                        
                        rows.sort(key=lambda r: r['y'])
                        
                        cleaned_lines = []
                        seen_phrases = set()
                        
                        for row in rows:
                            row['items'].sort(key=lambda i: i['x'])
                            # 結合同一行文字並去重複
                            row_texts = []
                            for item in row['items']:
                                t = item['text'].strip()
                                if t not in row_texts:
                                    row_texts.append(t)
                            
                            full_line = "   ".join(row_texts)
                            
                            # 濾走頁首重複雜訊
                            if any(k in full_line for k in ["OUTATON", "項目Item", "內容Descriptions", "數量Qty", "單價", "金額Price"]):
                                if "Re:" not in full_line and "編號Ref" not in full_line:
                                    continue
                            
                            # 避免完全相同的連續行重複
                            if full_line and full_line not in seen_phrases:
                                seen_phrases.add(full_line)
                                cleaned_lines.append(full_line)
                                
                        raw_text = "\n\n".join(cleaned_lines)
                    else:
                        raw_text = res.get('ParsedResults', [{}])[0].get('ParsedText', '')
                
                st.session_state['clean_output'] = raw_text
                st.success("🎉 還原成功，已自動過濾重複內容！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'clean_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 乾淨排版預覽與複製")
    st.write("行與行之間已適當留白，你可以直接在下方文字格複製：")
    
    st.text_area("乾淨文本", value=st.session_state['clean_output'], height=500, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['clean_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
