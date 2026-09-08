import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單表格格式還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單表格格式還原工具")
st.write("上載 PDF 或相片，直接還原為專業報價單 Markdown 表格格式（已加入項目分隔線）！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始還原表格格式", type="primary", use_container_width=True):
        with st.spinner("🤖 正在智能過濾重覆並加入項目分隔線..."):
            try:
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    raw_text = ""
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: raw_text += t + "\n"
                    st.session_state['table_output'] = raw_text
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
                        
                        # 建立 Markdown 表格開頭
                        markdown_table = "| 項目 Item | 內容 Descriptions | 數量 Qty | 單價 Unit Price | 金額 Price |\n"
                        markdown_table += "| :--- | :--- | :---: | :---: | :---: |\n"
                        
                        seen_rows = set()
                        for row in rows:
                            # 按照 X 軸由左到右排序
                            row['items'].sort(key=lambda i: i['x'])
                            
                            row_texts = []
                            for item in row['items']:
                                t = item['text'].strip()
                                if t and t not in row_texts:
                                    row_texts.append(t)
                            
                            full_line = " ".join(row_texts)
                            
                            # 過濾掉頁首及標題的重覆雜訊
                            if any(w in full_line.lower() for w in ["項目 item", "descriptions", "數量 qty", "單價", "金額price", "outaton"]):
                                if "re:" not in full_line.lower() and "編號" not in full_line:
                                    continue
                            
                            if full_line in seen_rows:
                                continue
                            seen_rows.add(full_line)
                            
                            col_item = row_texts[0] if len(row_texts) > 0 else ""
                            col_desc = " ".join(row_texts[1:-2]) if len(row_texts) > 3 else (full_line if len(row_texts) <= 2 else "")
                            col_qty = row_texts[-2] if len(row_texts) > 2 else ""
                            col_price = row_texts[-1] if len(row_texts) > 1 else ""
                            
                            # 💡 檢測如果第一欄係獨立數字（例如 1, 2, 3...），自動加一條間隔行作區分
                            if col_item.isdigit() and int(col_item) > 0:
                                markdown_table += f"| --- | --- | --- | --- | --- |\n"
                                
                            markdown_table += f"| {col_item} | {col_desc} | {col_qty} | {col_price} | |\n"
                            
                        st.session_state['table_output'] = markdown_table
                    else:
                        st.session_state['table_output'] = res.get('ParsedResults', [{}])[0].get('ParsedText', '無法讀取')
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")
            
            if 'table_output' in st.session_state:
                st.success("🎉 報價單表格格式還原成功（已按大 Item 加入分隔線）！")

if 'table_output' in st.session_state:
    st.markdown("---")
    st.subheader("📋 報價單 Markdown 表格預覽")
    st.write("你可以直接預覽表格，或在下方格子內複製：")
    
    # 預覽 Markdown 表格
    st.markdown(st.session_state['table_output'])
    
    st.markdown("### 📝 原始表格文本（方便複製）")
    st.text_area("Markdown 原始碼", value=st.session_state['table_output'], height=400, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['table_output']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
