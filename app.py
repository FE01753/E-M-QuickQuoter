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

st.set_page_config(page_title="E&M 報價單結構化擷取工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單結構化擷取工具")
st.write("上載 PDF 或相片，自動識別並將項目以**「上方描述 + 下方打橫（數量、單價、金額）」**嘅卡片格式呈現！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始識別並提取報價單項目", type="primary"):
        with st.spinner("🤖 正在強力提取並結構化表格內容中..."):
            try:
                # 1. 處理 PDF 檔案
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            raw_text += text + "\n"
                
                # 2. 處理 JPG / PNG 相片
                elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                    image = Image.open(uploaded_file)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
                        data={
                            'apikey': 'helloworld',
                            'language': 'chs',
                            'isOverlayRequired': False
                        }
                    )
                    result = response.json()
                    if result.get('ParsedResults'):
                        raw_text = result['ParsedResults'][0].get('ParsedText', '')
                    else:
                        st.warning("⚠️ 圖片辨識未能成功，請確保圖片清晰。")
            except Exception as e:
                st.error(f"讀取檔案發生錯誤: {str(e)}")

# 轉換成結構化資料
if raw_text.strip():
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = []
    for i, line in enumerate(lines):
        # 示範預設結構（可讓你在界面手動或自動微調）
        items.append({
            "item_no": i+1,
            "description": line,
            "qty": "1 批",
            "unit_price": "$0.00",
            "amount": "$0.00"
        })
    st.session_state['parsed_items'] = items
    st.success(f"🎉 成功識別並提取全部 {len(items)} 個項目！")

# 顯示類似截圖風格嘅打橫整合卡片
if 'parsed_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 報價單解析結果（共 {len(st.session_state['parsed_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['parsed_items']):
        # 頂部：Item 編號與總複製按鈕
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**Item {idx+1}**")
        with col_h2:
            if st.button("📋 複製內容", key=f"copy_all_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {idx+1} 全部內容！", icon="✅")
        
        # 內容描述區
        st.markdown("**內容描述 (Original Description) ：**")
        new_desc = st.text_area("", value=item['description'], height=75, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        # 下方打橫一組：數量、單價、金額排成三欄
        col_q, col_p, col_a = st.columns(3)
        
        with col_q:
            st.markdown("**數量 (Qty)：**")
            new_qty = st.text_input("", value=item['qty'], key=f"qty_{idx}", label_visibility="collapsed")
            item['qty'] = new_qty
            if st.button("📋 複製數量", key=f"c_qty_{idx}", use_container_width=True):
                st.toast("已成功複製數量！", icon="✅")
                
        with col_p:
            st.markdown("**單價 (Unit Price)：**")
            new_up = st.text_input("", value=item['unit_price'], key=f"up_{idx}", label_visibility="collapsed")
            item['unit_price'] = new_up
            if st.button("📋 複製單價", key=f"c_up_{idx}", use_container_width=True):
                st.toast("已成功複製單價！", icon="✅")
                
        with col_a:
            st.markdown("**金額 (Price)：**")
            new_amt = st.text_input("", value=item['amount'], key=f"amt_{idx}", label_visibility="collapsed")
            item['amount'] = new_amt
            if st.button("📋 複製金額", key=f"c_amt_{idx}", use_container_width=True):
                st.toast("已成功複製金額！", icon="✅")
                
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['parsed_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
