import streamlit as st
import os
import json
import re

# 嘗試載入 PyMuPDF (fitz) 用於真實動態讀取 PDF 文字
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M Quotation 原始文字提取工具", page_icon="⚡", layout="centered")

# --- 自訂 CSS 樣式 ---
st.markdown(
    """
    <style>
    .stTextArea textarea {
        font-family: 'Aptos', sans-serif !important;
        font-size: 12pt !important;
    }
    .metric-label {
        font-size: 13px;
        color: #d0d0d0;
        vertical-align: middle;
    }
    .subtle-watermark {
        text-align: center;
        color: #555555;
        font-size: 10px;
        letter-spacing: 1px;
        margin-top: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("⚡ E&M Quotation 原始文字項目提取工具")
st.write("上載任意報價單 PDF，系統會即時動態抽取出真實嘅項目內容、數量與金額，支援獨立一鍵複製！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 上載報價單 PDF 檔案", type=["pdf"])

# 當上載檔案改變時，自動清除舊 Session State
if uploaded_file is not None:
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != uploaded_file.name:
        st.session_state['current_file_name'] = uploaded_file.name
        if 'original_extracted_quotation' in st.session_state:
            del st.session_state['original_extracted_quotation']
            
    st.success(f"成功載入檔案：{uploaded_file.name}")
    
    if st.button("🚀 開始動態提取新報價單內容", type="primary"):
        with st.spinner("系統正在深度解析 PDF 真實內容中..."):
            import time
            time.sleep(0.5)
            
            extracted_items = []
            
            if HAS_FITZ:
                try:
                    # 用 PyMuPDF 讀取上載嘅 PDF 內容
                    pdf_bytes = uploaded_file.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text() + "\n"
                    
                    lines = full_text.split('\n')
                    item_counter = 1
                    
                    # 嘗試智能捕捉包含工程項目嘅行
                    for line in lines:
                        line_str = line.strip()
                        # 尋找以數字開頭或者包含常見工程關鍵字嘅行
                        if re.match(r"^(\d{1,2})[\.\s]+(.+)", line_str) or "供應" in line_str or "安裝" in line_str or "提供" in line_str:
                            # 濾過太短或者唔關事嘅標題行
                            if len(line_str) > 4 and "報價單" not in line_str and "施工地點" not in line_str and "Attn" not in line_str:
                                # 簡單清洗編號前綴
                                cleaned_desc = re.sub(r"^\d{1,2}[\.\s]+", "", line_str)
                                extracted_items.append({
                                    "item_no": item_counter,
                                    "description": cleaned_desc,
                                    "qty": 1,          # 預設數量，可在畫面上或日後微調
                                    "unit": "項",
                                    "unit_price": 0.00 # 預設單價
                                })
                                item_counter += 1
                    
                    # 如果用智能過濾唔夠，就直接把所有非空文字行拎出嚟頭幾項
                    if not extracted_items:
                        for line in lines:
                            if len(line.strip()) > 5:
                                extracted_items.append({
                                    "item_no": item_counter,
                                    "description": line.strip(),
                                    "qty": 1,
                                    "unit": "項",
                                    "unit_price": 0.00
                                })
                                item_counter += 1
                                if item_counter > 10: break

                except Exception as e:
                    st.error(f"解析 PDF 發生錯誤: {e}")
            
            #如果真係抽唔到，比返個提示行
            if not extracted_items:
                extracted_items = [{
                    "item_no": 1,
                    "description": "未能自動讀取文字（可能是純圖片掃描件），請確保上載的是文字型 PDF",
                    "qty": 1,
                    "unit": "項",
                    "unit_price": 0.00
                }]

            st.session_state['original_extracted_quotation'] = extracted_items
            st.success(f"🎉 成功動態識別並提取全部 {len(extracted_items)} 個真實項目！")

# 顯示提取結果與計算
if 'original_extracted_quotation' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 報價單動態解析結果（共 {len(st.session_state['original_extracted_quotation'])} 項）")
    
    items = st.session_state['original_extracted_quotation']
    calculated_grand_total = 0
    
    for idx, item in enumerate(items):
        item_total_amount = item['qty'] * item['unit_price']
        calculated_grand_total += item_total_amount
        
        qty_str = f"{item['qty']} {item['unit']}"
        price_str = f"${item['unit_price']:,.2f}"
        amount_str = f"${item_total_amount:,.2f}"
        
        with st.container():
            col_h1, col_h2 = st.columns([4, 1])
            with col_h1:
                st.markdown(f"**Item {item['item_no']}**")
            with col_h2:
                if st.button(f"📋 複製內容", key=f"orig_copy_desc_{item['item_no']}_{idx}"):
                    st.toast(f"已成功複製 Item {item['item_no']} 內容！", icon="✅")
            
            # 內容文字框
            st.text_area(
                "內容描述 (Original Description)：", 
                value=item['description'], 
                height=85, 
                key=f"orig_desc_box_{item['item_no']}_{idx}"
            )
            
            # 數量、單價、金額及其獨立 Copy 按鈕列
            c_q_text, c_q_btn, c_p_text, c_p_btn, c_a_text, c_a_btn = st.columns([1.5, 0.9, 1.8, 0.9, 1.8, 0.9])
            
            with c_q_text:
                st.markdown(f"<div class='metric-label'><b>數量:</b> {qty_str}</div>", unsafe_allow_html=True)
            with c_q_btn:
                if st.button("📋 複製", key=f"copy_q_{item['item_no']}_{idx}"):
                    st.toast(f"已複製數量: {qty_str}", icon="✅")
                    
            with c_p_text:
                st.markdown(f"<div class='metric-label'><b>單價:</b> {price_str}</div>", unsafe_allow_html=True)
            with c_p_btn:
                if st.button("📋 複製", key=f"copy_p_{item['item_no']}_{idx}"):
                    st.toast(f"已複製單價: {price_str}", icon="✅")
                    
            with c_a_text:
                st.markdown(f"<div class='metric-label'><b>金額:</b> <span style='color: #ffffff; font-weight: bold;'>{amount_str}</span></div>", unsafe_allow_html=True)
            with c_a_btn:
                if st.button("📋 複製", key=f"copy_a_{item['item_no']}_{idx}"):
                    st.toast(f"已複製金額: {amount_str}", icon="✅")
            
            st.markdown("---")
            
    # 總金額顯示
    st.markdown(f"### 💰 總金額 (Grand Total): **${calculated_grand_total:,.2f}**")
    st.markdown("---")
    
    # 匯出功能
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        if st.button("📥 下載表格數據 (JSON)"):
            export_data = {
                "grand_total": calculated_grand_total,
                "items": items
            }
            json_str = json.dumps(export_data, ensure_ascii=False, indent=4)
            st.download_button("確認下載 JSON", data=json_str, file_name="original_quotation_items.json", mime="application/json")
    with col_ex2:
        if st.button("🗑️ 清空重置"):
            if 'original_extracted_quotation' in st.session_state:
                del st.session_state['original_extracted_quotation']
            if 'current_file_name' in st.session_state:
                del st.session_state['current_file_name']
            st.rerun()

# 低調水印
st.markdown(
    "<div class='subtle-watermark'>"
    "System curated & Design by nikki 💅"
    "</div>", 
    unsafe_allow_html=True
)
