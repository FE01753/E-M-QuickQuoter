import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單表格文字還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單表格文字還原工具")
st.write("上載 PDF 或相片，直接轉為 Excel 適用嘅整齊表格文字格式，方便一鍵複製！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始轉化表格文字", type="primary", use_container_width=True):
        with st.spinner("🤖 正在提取並轉化為 Excel 表格格式..."):
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
                                if abs(row['y'] - top_y) < 14:
                                    row['items'].append({'x': left_x, 'text': text_str})
                                    placed = True
                                    break
                            if not placed:
                                rows.append({'y': top_y, 'items': [{'x': left_x, 'text': text_str}]})
                        
                        rows.sort(key=lambda r: r['y'])
                        
                        # 建立純文字表格（用 Tab 分隔，最適合直接貼入 Excel）
                        excel_text_lines = ["項目 Item\t內容 Descriptions\t數量 Qty\t單價 Unit Price\t金額 Price"]
                        
                        seen_lines = set()
                        for row in rows:
                            row['items'].sort(key=lambda i: i['x'])
                            row_texts = []
                            for item in row['items']:
                                t = item['text'].strip()
                                if t not in row_texts:
                                    row_texts.append(t)
                            
                            full_line = " ".join(row_texts)
                            
                            # 過濾頁首雜訊
                            if any(k in full_line for k in ["OUTATON", "項目Item", "內容Descriptions", "數量Qty", "單價", "金額Price"]):
                                continue
                                
                            if full_line and full_line not in seen_lines:
                                seen_lines.add(full_line)
                                
                                col_item = row_texts[0] if len(row_texts) > 0 else ""
                                col_desc = " ".join(row_texts[1:-2]) if len(row_texts) > 3 else full_line
                                col_qty = row_texts[-2] if len(row_texts) > 2 else ""
                                col_price = row_texts[-1] if len(row_texts) > 1 else ""
                                
                                # 用 \t (Tab鍵) 分隔每一格，咁樣貼落 Excel 會自動入唔同嘅格
                                excel_text_lines.append(f"{col_item}\t{col_desc}\t{col_qty}\t{col_price}\t")
                                
                        st.session_state['excel_table_text'] = "\n".join(excel_text_lines)
                    else:
                        st.session_state['excel_table_text'] = "無法讀取內容"
                
                st.success("🎉 表格文字轉化成功！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'excel_table_text' in st.session_state:
    st.markdown("---")
    st.subheader("📋 Excel 專用表格文字（可直接全選複製貼上）")
    st.write("底下嘅格子入面全部都係對齊好嘅表格文字，直接 Copy 就可以貼入 Excel 或系統：")
    
    # 乾淨嘅文字輸入格，不再包含任何 HTML 碼
    st.text_area("Excel 表格文本", value=st.session_state['excel_table_text'], height=450, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['excel_table_text']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
