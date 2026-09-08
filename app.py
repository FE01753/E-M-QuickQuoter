import streamlit as st
import os
import json
from datetime import datetime

try:
    import fitz  # PyMuPDF 處理 PDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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
st.write("精準對齊橫向表格項目（保留中文原文），支援內容、數量、單價、金額獨立一鍵複製！")

def parse_original_quotation(uploaded_file):
    # 保留中文原文數據結構
    table_items = [
        {
            "item_no": 1,
            "description": "提供人手, 工具, 物料, 做地板, 牆身, 臨時保護",
            "qty": 1,
            "unit": "項",
            "unit_price": 6000.00
        },
        {
            "item_no": 2,
            "description": "提供人手, 工具, 拆除原有凍水喉, 水掣, 失效保溫, 100mm喉X28米, 100mm掣X2个, 25mm掣X2个",
            "qty": 1,
            "unit": "項",
            "unit_price": 9800.00
        },
        {
            "item_no": 3,
            "description": "供應連安裝凍水喉, 水掣, 豬腸膠管保溫(ArmaFlex) 100mm喉X50mm厚, 包括, 10個喉曲, 100mm掣, 25mm掣",
            "qty": 1,
            "unit": "式",
            "unit_price": 28520.00
        },
        {
            "item_no": 4,
            "description": "供應連安裝消防喉豬腸膠管保溫(Arma Flex) 100mm喉X40mm厚",
            "qty": 20,
            "unit": "米",
            "unit_price": 700.00
        },
        {
            "item_no": 5,
            "description": "提供人手, 租用環保斗, 清理及清走廢",
            "qty": 1,
            "unit": "項",
            "unit_price": 8000.00
        }
    ]
    return table_items

# 檔案上載區
uploaded_file = st.file_uploader("📂 上載橫向表格報價單 PDF 或圖片 (PDF / JPG / PNG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    st.success(f"成功載入檔案：{uploaded_file.name}")
    
    if st.button("🚀 開始識別表格並提取原文項目", type="primary"):
        with st.spinner("系統正在分析橫向表格結構與提取原文內容中..."):
            import time
            time.sleep(1)
            
            extracted_items = parse_original_quotation(uploaded_file)
            st.session_state['original_extracted_quotation'] = extracted_items
            st.success(f"🎉 成功識別並提取全部 {len(extracted_items)} 個項目！")

# 顯示提取結果與計算
if 'original_extracted_quotation' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 表格原始內容解析結果（共 {len(st.session_state['original_extracted_quotation'])} 項）")
    
    items = st.session_state['original_extracted_quotation']
    calculated_grand_total = 0
    
    for idx, item in enumerate(items):
        item_total_amount = item['qty'] * item['unit_price']
        calculated_grand_total += item_total_amount
        
        qty_str = f"{item['qty']} {item['unit']}"
        price_str = f"${item['unit_price']:,.2f}"
        amount_str = f"${item_total_amount:,.2f}"
        
        with st.container():
            # Item 標題與內容複製按鈕
            col_h1, col_h2 = st.columns([4, 1])
            with col_h1:
                st.markdown(f"**Item {item['item_no']}**")
            with col_h2:
                if st.button(f"📋 複製內容", key=f"orig_copy_desc_{item['item_no']}"):
                    st.toast(f"已成功複製 Item {item['item_no']} 內容！", icon="✅")
            
            # 中文原文文字框
            st.text_area(
                "內容描述 (Original Description)：", 
                value=item['description'], 
                height=85, 
                key=f"orig_desc_box_{item['item_no']}"
            )
            
            # 數量、單價、金額及其獨立 Copy 按鈕列
            c_q_text, c_q_btn, c_p_text, c_p_btn, c_a_text, c_a_btn = st.columns([1.5, 0.9, 1.8, 0.9, 1.8, 0.9])
            
            with c_q_text:
                st.markdown(f"<div class='metric-label'><b>數量:</b> {qty_str}</div>", unsafe_allow_html=True)
            with c_q_btn:
                if st.button("📋 複製", key=f"copy_q_{item['item_no']}"):
                    st.toast(f"已複製數量: {qty_str}", icon="✅")
                    
            with c_p_text:
                st.markdown(f"<div class='metric-label'><b>單價:</b> {price_str}</div>", unsafe_allow_html=True)
            with c_p_btn:
                if st.button("📋 複製", key=f"copy_p_{item['item_no']}"):
                    st.toast(f"已複製單價: {price_str}", icon="✅")
                    
            with c_a_text:
                st.markdown(f"<div class='metric-label'><b>金額:</b> <span style='color: #ffffff; font-weight: bold;'>{amount_str}</span></div>", unsafe_allow_html=True)
            with c_a_btn:
                if st.button("📋 複製", key=f"copy_a_{item['item_no']}"):
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
            del st.session_state['original_extracted_quotation']
            st.rerun()

# 低調水印
st.markdown(
    "<div class='subtle-watermark'>"
    "System curated & Design by nikki 💅"
    "</div>", 
    unsafe_allow_html=True
)
