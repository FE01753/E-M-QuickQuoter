import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單空間原貌還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單空間原貌還原工具")
st.write("上載 PDF 或相片，自動按橫向座標對齊，適當加入空格並放大文字格！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原橫向報價單格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在優化間距與還原空間排版..."):
            try:
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    raw_text = ""
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: raw_text += t + "\n"
                    st.session_state['spatial_output'] = raw_text
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
                                if abs(row['y'] - top_y) < 12:  # 12像素內視為同一橫行
                                    row['items'].append({'x': left_x, 'text': text_str})
                                    placed = True
                                    break
                            if not placed:
                                rows.append({'y': top_y, 'items': [{'x': left_x, 'text': text_str}]})
                        
                        # 按照 Y 軸由上到下排序
                        rows.sort(key=lambda r: r['y'])
                        
                        formatted_lines = []
                        for row in rows:
                            # 按照 X 軸由左到右排序
                            row['items'].sort(key=lambda i: i['x'])
                            
                            # 根據 X 軸距離智能補上適當空格，保持欄位排版
                            line_str = ""
                            last_x = 0
                            for item in row['items']:
                                current_x = item['x']
                                if last_x > 0:
                                    # 計算距離差，大約每 50 像素補一個 tab/space 距離
                                    diff = current_x - last_x
                                    spaces = max(2, int(diff / 25))
                                    line_str += " " * spaces
                                else:
                                    line_str += ""
                                line_str += item['text']
                                last_x = current_x + len(item['text']) * 8  # 粗略估算字寬
                                
                            formatted_lines.append(line_str)
                            
                        st.session_state['spatial_output'] = "\n".join(formatted_lines)
                    else:
                        st.session_state['spatial_output'] = res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")
            
            if 'spatial_output' in st.session_state:
                st.success("🎉 空間橫向格式還原成功！")

if 'spatial_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 橫向對齊還原結果（已優化間距）")
    st.write("你可以直接在下方放大嘅格子入面全選複製：")
    
    # 放大個格 (height=450)，方便閱讀同 COPY
    st.text_area("還原文本", value=st.session_state['spatial_output'], height=450, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['spatial_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
