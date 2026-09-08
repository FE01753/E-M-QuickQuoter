import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單空間原貌還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單空間原貌還原工具")
st.write("上載 PDF 或相片，完美還原橫向表格結構，絕不走樣！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原橫向報價單格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在還原空間排版與橫向對齊結構..."):
            try:
                # 這裡改用 OCR.space 的文字疊加與區域檢測 (isOverlayRequired=True) 來獲取坐標
                image = None
                if file_name.endswith('.pdf') and HAS_PDF:
                    # 如果是PDF，嘗試轉成圖片送去OCR以獲取坐標
                    reader = PdfReader(uploaded_file)
                    # 簡化處理：讀取第一頁文字或轉圖（這裡用基礎文字行重組 fallback）
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
                        
                        # 根據 Y 軸坐標 (Top) 將文字分行，若 Y 接近（例如差 10 像素內）則代表在同一行
                        rows = []
                        for line in lines_data:
                            # 取該行第一個字元的 Top 坐標
                            words = line.get('Words', [])
                            if not words: continue
                            top_y = words[0]['Top']
                            left_x = words[0]['Left']
                            text_str = "".join([w['WordText'] for w in words])
                            
                            # 尋找是否已有相近的 Y 軸 row
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
                            # 按照 X 軸由左到右排序同一行的文字
                            row['items'].sort(key=lambda i: i['x'])
                            line_text = "   ".join([item['text'] for item in row['items']])
                            formatted_lines.append(line_text)
                            
                        st.session_state['spatial_output'] = "\n".join(formatted_lines)
                    else:
                        # Fallback
                        st.session_state['spatial_output'] = res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")
            
            if 'spatial_output' in st.session_state:
                st.success("🎉 空間橫向格式還原成功！")

if 'spatial_output' in st.session_state:
    st.markdown("---")
    st.subheader("📄 橫向對齊還原結果")
    st.write("你可以直接在下方全選複製：")
    
    st.text_area("還原文本", value=st.session_state['spatial_output'], height=400, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['spatial_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
