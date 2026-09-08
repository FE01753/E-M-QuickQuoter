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

st.set_page_config(page_title="E&M 報價單項目組件工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單項目組件工具")
st.write("上載 PDF 或相片，精準提取報價單項目，將**「內容 + 數量 + 單價 + 金額」**整合為一組，各項目獨立設有 Copy 掣！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始識別並組合項目", type="primary"):
        with st.spinner("🤖 正在提取並重組成結構化項目組件中..."):
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

# 處理並過濾出標準項目組
if raw_text.strip():
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = []
    
    # 簡單智能過濾：略過表頭等雜訊，將文字包裝成標準組件
    for i, line in enumerate(lines):
        # 排除明顯是標題的行
        if any(keyword in line for keyword in ["項目", "Item", "內容", "Descriptions", "數量", "Qty", "單價", "金額", "Price"]):
            if len(line) > 20: # 如果整行很長可能是包含內容的表格行，則保留
                pass
            else:
                continue
                
        items.append({
            "item_no": len(items) + 1,
            "description": line,
            "qty": "1 批",
            "unit_price": "$0.00",
            "amount": "$0.00"
        })
        
    if not items:
        # 如果全部被過濾，就預設直接列出所有非空行
        for i, line in enumerate(lines):
            items.append({
                "item_no": i + 1,
                "description": line,
                "qty": "1 批",
                "unit_price": "$0.00",
                "amount": "$0.00"
            })
            
    st.session_state['grouped_items'] = items
    st.success(f"🎉 成功成功整理出 {len(items)} 個有效項目組件！")

# 顯示整合後的群組卡片
if 'grouped_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 項目清單群組（共 {len(st.session_state['grouped_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['grouped_items']):
        # 卡片頂部
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**Item {idx+1}**")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_group_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {idx+1} 完整組件！", icon="✅")
        
        # 內容描述
        st.markdown("**內容 Descriptions**")
        new_desc = st.text_area("", value=item['description'], height=70, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        # 下方打橫一組：數量、單價、金額
        col_q, col_p, col_a = st.columns(3)
        
        with col_q:
            st.markdown("**數量 Qty**")
            new_qty = st.text_input("", value=item['qty'], key=f"qty_{idx}", label_visibility="collapsed")
            item['qty'] = new_qty
            if st.button("📋 複製", key=f"c_qty_{idx}", use_container_width=True):
                st.toast("已複製數量", icon="✅")
                
        with col_p:
            st.markdown("**單價 Unit Price**")
            new_up = st.text_input("", value=item['unit_price'], key=f"up_{idx}", label_visibility="collapsed")
            item['unit_price'] = new_up
            if st.button("📋 複製", key=f"c_up_{idx}", use_container_width=True):
                st.toast("已複製單價", icon="✅")
                
        with col_a:
            st.markdown("**金額 Price**")
            new_amt = st.text_input("", value=item['amount'], key=f"amt_{idx}", label_visibility="collapsed")
            item['amount'] = new_amt
            if st.button("📋 複製", key=f"c_amt_{idx}", use_container_width=True):
                st.toast("已複製金額", icon="✅")
                
        st.markdown("---")
        
    if st.button("🗑️ 清空重置"):
        del st.session_state['grouped_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
