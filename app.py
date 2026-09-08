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

st.set_page_config(page_title="E&M 報價單項目智能解析工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單項目智能解析工具")
st.write("上載 PDF 或相片，系統會**智能辨識並拆解**「內容 Descriptions」、「數量 Qty」、「單價 Unit Price」、「金額 Price」，並提供**真正嘅一鍵 Copy 掣**！")

# 智能正則解析函數 (專門針對香港 E&M 工程報價單格式)
def parse_em_quote_lines(raw_text):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    parsed_items = []
    
    # 忽略表格標題雜訊
    ignore_keywords = ["項目", "item", "描述", "descriptions", "數量", "qty", "單價", "unit price", "金額", "amount", "price", "頁", "page"]
    
    for line in lines:
        # 如果整行都是表頭，跳過
        if any(line.lower() == k for k in ignore_keywords) or len(line) < 3:
            continue
            
        # 尋找金額與單價 (例如 $29,700.00 / HKD 165.00 / 165.00)
        prices = re.findall(r'(\$?\s?[\d,]+\.\d{2}|\bHKD\s?[\d,]+\.\d{2}\b)', line)
        
        # 尋找數量 (例如 180 米 / 1 批 / 20 set / 5 nos)
        qty_match = re.search(r'(\d+\s*(?:米|批|套|個|項|座|件|組|set|sets|pc|pcs|m|nos|lot)\b)', line, re.IGNORECASE)
        
        qty = qty_match.group(1) if qty_match else ""
        
        unit_price = ""
        amount = ""
        if len(prices) >= 2:
            unit_price = prices[0]
            amount = prices[1]
        elif len(prices) == 1:
            amount = prices[0]
            
        # 清除已被提取為數量同金額嘅文字，剩下嘅就係 Description
        desc = line
        if qty:
            desc = desc.replace(qty, "")
        for p in prices:
            desc = desc.replace(p, "")
            
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        # 如果 desc 唔係純標題，就加入項目清單
        if desc and not any(desc.lower() == k for k in ignore_keywords):
            parsed_items.append({
                "item_no": len(parsed_items) + 1,
                "description": desc,
                "qty": qty if qty else "1 批",
                "unit_price": unit_price if unit_price else "--",
                "amount": amount if amount else "--"
            })
            
    return parsed_items

# 檔案上載區
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或相片 (JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

raw_text = ""

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    
    if st.button("🚀 開始識別並提取報價單項目", type="primary", use_container_width=True):
        with st.spinner("🤖 正在智能解析表格資料中..."):
            try:
                # 1. PDF 讀取
                if file_name.endswith('.pdf') and HAS_PDF:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
                # 2. 相片 OCR 讀取
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
                st.error(f"檔案讀取失敗: {str(e)}")

        if raw_text.strip():
            items = parse_em_quote_lines(raw_text)
            st.session_state['parsed_items'] = items
            st.success(f"🎉 成功成功識別並提取全部 {len(items)} 個真實項目！")

# 顯示解析結果卡片 (完全依照截圖排版)
if 'parsed_items' in st.session_state and st.session_state['parsed_items']:
    st.markdown("---")
    st.subheader(f"📋 報價單解析結果（共 {len(st.session_state['parsed_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['parsed_items']):
        st.markdown(f"### Item {idx+1}")
        
        # 內容描述
        st.markdown("**內容描述 (Original Description) ：**")
        new_desc = st.text_area("", value=item['description'], height=70, key=f"desc_{idx}", label_visibility="collapsed")
        item['description'] = new_desc
        
        # 原生一鍵 Copy 區（點擊文字框右上角即可 100% 複製到剪貼簿）
        col_q, col_p, col_a = st.columns(3)
        
        with col_q:
            st.caption("數量 Qty")
            st.code(item['qty'], language=None)
            
        with col_p:
            st.caption("單價 Unit Price")
            st.code(item['unit_price'], language=None)
            
        with col_a:
            st.caption("金額 Price")
            st.code(item['amount'], language=None)
            
        st.markdown("---")
        
    if st.button("🗑️ 清空重置", use_container_width=True):
        del st.session_state['parsed_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
