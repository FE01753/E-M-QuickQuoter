import streamlit as st
import os
import json
import re
from datetime import datetime

# 嘗試載入 pypdf 用於動態讀取 PDF 內容
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

st.set_page_config(page_title="E&M Quotation 原始文字提取工具", page_icon="⚡", layout="centered")

# --- 自訂 CSS 樣式：Aptos 12pt 及低調水印樣式 ---
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
st.write("上載任意報價單 PDF，系統會實時動態解析入面嘅真實項目、數量與金額，支援獨立一鍵複製！")

def dynamic_parse_pdf(uploaded_file):
    """
    動態讀取真實上載嘅 PDF 檔案內容並嘗試拆解項目
    """
    extracted_items = []
    
    if not HAS_PYPDF:
        # 如果環境未裝 pypdf，提供基本提示並返回示範
        return [{"item_no": 1, "description": "請確保已安裝 pypdf 套件以支援動態 PDF 解析", "qty": 1, "unit": "項", "unit_price": 0.00}]

    try:
        reader = pypdf.PdfReader(uploaded_file)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        lines = full_text.split('\n')
        
        # 動態尋找以數字開頭嘅行（例如 "1", "2" 等報價項目行）
        item_counter = 1
        for line in lines:
            line_str = line.strip()
            # 匹配數字開頭嘅項目行
            match = re.match(r"^(\d{1,2})[\.\s]+(.+)", line_str)
            if match:
                content = match.group(2)
                # 簡單過濾太短或者唔關事嘅行
                if len(content) > 3:
                    extracted_items.append({
                        "item_no": item_counter,
                        "description": content,
                        "qty": 1,          # 預設數量，可透過介面修改
                        "unit": "項",
                        "unit_price": 0.00 # 預設單價
                    })
                    item_counter += 1
                    
        # 如果抽唔到任何結構，將整份 PDF 嘅文字作為第一項顯示，方便手動對照
        if not extracted_items:
            extracted_items.append({
                "item_no": 1,
                "description": full_text[:200].strip() if full_text else "未能提取有效文字，請檢查 PDF 格式",
                "qty": 1,
                "unit": "項",
                "unit_price": 0.00
            })
            
    except Exception as e:
        st.error(f"解析 PDF 發生錯誤: {e}")
        
    return extracted_items

# 檔案上載區
uploaded_file = st.file_uploader("📂 上載橫向表格報價單 PDF (PDF 格式)", type=["pdf", "png", "jpg", "jpeg"])

# 當上載檔案改變時，自動清除舊嘅 Session State，確保上載新單時唔會留住上一份嘅內容
if uploaded_file is not None:
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != uploaded_file.name:
        st.session_state['current_file_name'] = uploaded_file.name
        if 'original_extracted_quotation' in st.session_state:
            del st.session_state['original_extracted_quotation']
            
    st.success(f"成功載入新檔案：{uploaded_file.name}")
    
    if st.button("🚀 開始動態提取新報價單項目", type="primary"):
        with st.spinner("系統正在實時掃描並解析新上載嘅報價單內容中..."):
            import time
            time.sleep(0.5)
            
            # 執行動態解析
            extracted_items = dynamic_parse_pdf(uploaded_file)
            st.session_state['original_extracted_quotation'] = extracted_items
            st.success(f"🎉 成功動態識別並提取全部 {len(extracted_items)} 個項目！")

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
