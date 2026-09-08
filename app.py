import streamlit as st
import json
import re
import requests
import io
from PIL import Image

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="E&M 報價單 Item 精準過濾工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單 Item 精準過濾工具")
st.write("上載 PDF 或相片，**嚴格只捉取帶有 Item 編號嘅項目**，自動合併斷行，確保乾淨俐落！")

uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始嚴格按 Item 提取", type="primary", use_container_width=True):
        with st.spinner("🤖 正在配對 Item 編號並過濾無關內容..."):
            try:
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
                elif file_name.endswith(('.png', '.jpg', 'jpeg')):
                    image = Image.open(uploaded_file)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={uploaded_file.name: img_byte_arr},
                        data={'apikey': 'helloworld', 'language': 'chs', 'isOverlayRequired': False}
                    )
                    res = response.json()
                    if res.get('ParsedResults'):
                        raw_text = res['ParsedResults'][0].get('ParsedText', '')
            except Exception as e:
                st.error(f"讀取錯誤: {str(e)}")

        if raw_text.strip():
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            parsed_items = []
            
            current_item = None
            
            for line in lines:
                # 略過表頭常見字眼
                if any(kw in line.lower() for kw in ["項目 item", "descriptions", "數量 qty", "單價", "金額 price", "page"]):
                    continue
                
                # 檢查呢行係唔係新嘅 Item 開始（例如以數字開頭，後面跟住空格或點，如 "1 ", "1.", "2   "）
                item_start_match = re.match(r'^(\d{1,3})\s*[\.\s]\s*(.*)', line)
                
                if item_start_match:
                    # 如果之前已經有一個 item，先儲存起佢
                    if current_item:
                        parsed_items.append(current_item)
                    
                    # 建立新 Item
                    item_num = item_start_match.group(1)
                    content = item_start_match.group(2)
                    
                    current_item = {
                        "item_no": item_num,
                        "raw_line": content,
                        "description": content,
                        "qty": "",
                        "unit_price": "",
                        "amount": ""
                    }
                else:
                    # 如果冇帶 item 數字，代表係上一行嘅延伸內容（例如 "100mmX40mm厚，"），直接拼埋落去上一行
                    if current_item:
                        current_item["description"] += " " + line
                        current_item["raw_line"] += " " + line
            
            # 記得加入最後一個 item
            if current_item:
                parsed_items.append(current_item)
            
            # 對每個捉到嘅 Item 進行後續拆解（抽數量同金額）
            final_items = []
            for item in parsed_items:
                text = item["raw_line"]
                
                # 抽金額
                prices = re.findall(r'(?:HKD|HK\$|\$)?\s*[\d,]+\.\d{2}', text)
                # 抽數量
                qty_match = re.search(r'(\d+\s*(?:項|米|批|套|個|件|組|set|sets|pc|pcs|m|nos|lot)\b)', text, re.IGNORECASE)
                qty = qty_match.group(1) if qty_match else ""
                
                unit_price = ""
                amount = ""
                if len(prices) >= 2:
                    unit_price = prices[0]
                    amount = prices[1]
                elif len(prices) == 1:
                    amount = prices[0]
                
                # 從 Description 入面清走已抽走嘅數量同銀碼
                desc = text
                if qty:
                    desc = desc.replace(qty, "")
                for p in prices:
                    desc = desc.replace(p, "")
                
                desc = re.sub(r'[\$\,\.]+$', '', desc).strip()
                desc = re.sub(r'\s+', ' ', desc)
                
                final_items.append({
                    "item_no": item["item_no"],
                    "description": desc,
                    "qty": qty,
                    "unit_price": unit_price,
                    "amount": amount
                })
            
            st.session_state['strict_items'] = final_items
            st.success(f"🎉 成功嚴格對應並提取 {len(final_items)} 個帶編號嘅真實項目！")

# 顯示結果
if 'strict_items' in st.session_state and st.session_state['strict_items']:
    st.markdown("---")
    st.subheader(f"📋 嚴格過濾後的項目清單（共 {len(st.session_state['strict_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['strict_items']):
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**Item {item['item_no']}**")
        with col_h2:
            if st.button("📋 複製整組", key=f"copy_group_{idx}", use_container_width=True):
                st.toast(f"已複製 Item {item['item_no']}！", icon="✅")
        
        st.markdown("**內容 Descriptions**")
        new_desc = st.text_area("", value=item['description'], height=75, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        col_q, col_p, col_a = st.columns(3)
        with col_q:
            st.markdown("**數量 Qty**")
            item['qty'] = st.text_input("", value=item['qty'], key=f"q_{idx}", placeholder="例如: 180米", label_visibility="collapsed")
        with col_p:
            st.markdown("**單價 Unit Price**")
            item['unit_price'] = st.text_input("", value=item['unit_price'], key=f"p_{idx}", placeholder="例如: $165.00", label_visibility="collapsed")
        with col_a:
            st.markdown("**金額 Price**")
            item['amount'] = st.text_input("", value=item['amount'], key=f"a_{idx}", placeholder="例如: $29,700", label_visibility="collapsed")
            
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['strict_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
