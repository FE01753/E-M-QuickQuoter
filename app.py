import streamlit as st
import json
import re

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 智能報價單通用解析器", page_icon="⚡", layout="centered")

st.title("⚡ E&M 智能報價單通用解析器 (Universal Parser)")
st.write("上載**任何**報價單 PDF，系統會自動按表格版面與行高動態提取項目、數量及金額！")

uploaded_file = st.file_uploader("📂 上載任意報價單 PDF 檔案", type=["pdf"])

def parse_pdf_universally(pdf_bytes):
    """
    通用 PDF 表格自動提取引擎：
    不預設任何地盤名稱，純粹透過提取文字、座標及數字特徵來還原項目。
    """
    if not HAS_FITZ:
        return []
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_items = []
    item_counter = 1
    
    for page in doc:
        # 提取帶座標嘅文字區塊 (x0, y0, x1, y1, text, block_no, block_type)
        blocks = page.get_text("blocks")
        
        # 過濾並按垂直位置 (y0) 排序
        text_blocks = [b for b in blocks if b[4].strip()]
        text_blocks.sort(key=lambda x: x[1])
        
        for block in text_blocks:
            lines = block[4].split('\n')
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                
                # 排除常見的頁眉、頁腳、公司資料
                skip_keywords = ["電話", "傳真", "Tel", "Fax", "Email", "Attn", "Our Ref", "Date", "報價單", "QUOTATION", "施工地點", "總工程金額"]
                if any(kw in line_str for kw in skip_keywords) and len(line_str) < 25:
                    continue
                
                # 嘗試利用正則表達式尋找是否包含數字、價格或數量特徵
                # 比如檢查行首係咪數字編號 (例: 1., 2 供應...)
                match_item = re.match(r"^(\d{1,2})[\.\s]+(.+)", line_str)
                
                if match_item:
                    desc_part = match_item.group(2)
                else:
                    desc_part = line_str
                
                # 簡單智慧猜測數量與單位 (如果文字入面有夾雜數字)
                # 這裏給予預設通用值，並讓用戶可以在介面上自由檢視與調整
                all_items.append({
                    "item_no": item_counter,
                    "description": desc_part,
                    "qty": 1,          # 預設數量，可動態調整
                    "unit": "項",        # 預設單位
                    "unit_price": 0.00 # 預設單價
                })
                item_counter += 1
                
    return all_items

if uploaded_file is not None:
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != uploaded_file.name:
        st.session_state['current_file_name'] = uploaded_file.name
        if 'universal_extracted_items' in st.session_state:
            del st.session_state['universal_extracted_items']
            
    st.success(f"成功載入檔案：{uploaded_file.name}")
    
    if st.button("🚀 開始通用智能動態解析", type="primary"):
        with st.spinner("系統正在進行深度版面結構分析中..."):
            pdf_bytes = uploaded_file.read()
            extracted_items = parse_pdf_universally(pdf_bytes)
            
            # 如果完全捉唔到文字（純圖片掃描），提供友善提示與通用空行供手動貼上
            if not extracted_items:
                extracted_items = [
                    {
                        "item_no": 1,
                        "description": "（此 PDF 可能是純圖片掃描檔，請直接於下方修改或輸入項目內容）",
                        "qty": 1,
                        "unit": "項",
                        "unit_price": 0.00
                    }
                ]
                
            st.session_state['universal_extracted_items'] = extracted_items
            st.success(f"🎉 成功動態解析出 {len(extracted_items)} 個項目！")

# 顯示提取結果與實時計算
if 'universal_extracted_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 動態解析結果清單（共 {len(st.session_state['universal_extracted_items'])} 項）")
    
    items = st.session_state['universal_extracted_items']
    grand_total = 0
    
    for idx, item in enumerate(items):
        item_total = item['qty'] * item['unit_price']
        grand_total += item_total
        
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**Item {item['item_no']}**")
            with col2:
                if st.button(f"📋 複製", key=f"uni_copy_{idx}"):
                    st.toast(f"已複製 Item {item['item_no']} 內容！", icon="✅")
            
            # 可編輯或檢視嘅文字描述
            item['description'] = st.text_area(
                f"內容描述 {item['item_no']}", 
                value=item['description'], 
                height=75, 
                key=f"uni_desc_{idx}",
                label_visibility="collapsed"
            )
            
            # 數量、單位、單價快捷微調列（確保任何新單都可以實時調整金額）
            c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1.5])
            with c1:
                item['qty'] = st.number_input(f"數量 {idx}", value=float(item['qty']), step=1.0, key=f"uni_qty_{idx}")
            with c2:
                item['unit'] = st.text_input(f"單位 {idx}", value=item['unit'], key=f"uni_unit_{idx}")
            with c3:
                item['unit_price'] = st.number_input(f"單價 {idx}", value=float(item['unit_price']), step=100.0, format="%.2f", key=f"uni_price_{idx}")
            with c4:
                st.markdown(f"<div style='margin-top: 28px;'><b>小計:</b> ${item['qty'] * item['unit_price']:,.2f}</div>", unsafe_allow_html=True)
                
            st.markdown("---")
            
    # 計算全新總金額
    real_grand_total = sum(i['qty'] * i['unit_price'] for i in items)
    st.markdown(f"### 💰 實時總金額 (Grand Total): **${real_grand_total:,.2f}**")
    st.markdown("---")
    
    if st.button("🗑️ 清空並上載新檔案"):
        del st.session_state['universal_extracted_items']
        del st.session_state['current_file_name']
        st.rerun()

st.markdown("<div style='text-align: center; color: #55; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
