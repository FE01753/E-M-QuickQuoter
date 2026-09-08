import streamlit as st
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="報價單表格分隔還原工具", page_icon="⚡", layout="centered")

st.title("⚡ 報價單表格分隔還原工具")
st.write("上載 PDF 或相片，自動以帶框線嘅專業表格顯示，並提供 HTML / Markdown 原始碼方便複製！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始生成分隔表格", type="primary", use_container_width=True):
        with st.spinner("🤖 正在重組欄位並製作分隔表格..."):
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
                        
                        # 建立靚仔嘅 HTML 表格（帶有實線格線）
                        html_table = """
                        <table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px;">
                          <thead>
                            <tr style="background-color: #f2f2f2; border-bottom: 2px solid #ddd;">
                              <th style="border: 1px solid #ddd; padding: 10px; text-align: center; width: 10%;">項目 Item</th>
                              <th style="border: 1px solid #ddd; padding: 10px; text-align: left; width: 45%;">內容 Descriptions</th>
                              <th style="border: 1px solid #ddd; padding: 10px; text-align: center; width: 15%;">數量 Qty</th>
                              <th style="border: 1px solid #ddd; padding: 10px; text-align: right; width: 15%;">單價 Unit Price</th>
                              <th style="border: 1px solid #ddd; padding: 10px; text-align: right; width: 15%;">金額 Price</th>
                            </tr>
                          </thead>
                          <tbody>
                        """
                        
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
                                
                                # 嘗試智能分配欄位 (Item, Desc, Qty, Price)
                                col_item = row_texts[0] if len(row_texts) > 0 else ""
                                col_desc = " ".join(row_texts[1:-2]) if len(row_texts) > 3 else full_line
                                col_qty = row_texts[-2] if len(row_texts) > 2 else ""
                                col_price = row_texts[-1] if len(row_texts) > 1 else ""
                                
                                html_table += f"""
                                <tr style="border-bottom: 1px solid #ddd;">
                                  <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">{col_item}</td>
                                  <td style="border: 1px solid #ddd; padding: 10px; text-align: left;">{col_desc}</td>
                                  <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">{col_qty}</td>
                                  <td style="border: 1px solid #ddd; padding: 10px; text-align: right;">{col_price}</td>
                                  <td style="border: 1px solid #ddd; padding: 10px; text-align: right;"></td>
                                </tr>
                                """
                                
                        html_table += "  </tbody>\n</table>"
                        st.session_state['table_html'] = html_table
                    else:
                        st.session_state['table_html'] = "<p>無法讀取內容</p>"
                
                st.success("🎉 分隔表格生成成功！")
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

if 'table_html' in st.session_state:
    st.markdown("---")
    st.subheader("📋 表格預覽（帶清晰格線分隔）")
    
    # 直接在 Streamlit 渲染出帶邊框嘅 HTML 表格
    st.markdown(st.session_state['table_html'], unsafe_allow_html=True)
    
    st.markdown("### 📝 HTML 原始碼（方便複製貼落網頁或系統）")
    st.text_area("HTML Source", value=st.session_state['table_html'], height=250, label_visibility="collapsed")
    
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['table_html']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
