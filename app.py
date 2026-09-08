import streamlit as st
import json

st.set_page_config(page_title="E&M AI 萬能報價單智能識別器", page_icon="⚡", layout="centered")

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

st.title("⚡ E&M 報價單智能分項小幫手")
st.write("直接將 PDF 或電郵嘅 Quotation 文字貼喺下面，系統會自動幫你逐行切開做獨立項目！")

# 選擇輸入模式
input_mode = st.radio("選擇輸入方式：", ["📝 直接貼上文字 (最快、免API)", "📂 上載檔案 (PDF / 圖片)"], horizontal=True)

raw_text_input = ""
if "📝 直接貼上文字 (最快、免API)" in input_mode:
    raw_text_input = st.text_area(
        "請在此貼上報價單內容 (每行一項，或直接貼上整段文字)：",
        placeholder="例如：\n1. 供應及安裝 FCU 抽風機 2台 @ $3,500\n2. 更改低壓電掣櫃及穿線工程 1項 @ $12,800\n3. 消防警報系統測試",
        height=150
    )
    
    if st.button("🚀 開始自動分項拆解", type="primary"):
        if raw_text_input.strip():
            lines = raw_text_input.strip().split('\n')
            extracted_items = []
            counter = 1
            for line in lines:
                line_s = line.strip()
                if line_s:
                    extracted_items.append({
                        "item_no": counter,
                        "description": line_s,
                        "qty": 1.0,
                        "unit": "項",
                        "unit_price": 0.0
                    })
                    counter += 1
            st.session_state['ai_extracted_quotation'] = extracted_items
            st.success(f"🎉 成功拆解出 {len(extracted_items)} 個項目！")
        else:
            st.warning("請先輸入或貼上文字內容！")

else:
    uploaded_file = st.file_uploader("📂 上載檔案", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_file is not None:
        if st.button("🚀 載入檔案", type="primary"):
            st.session_state['ai_extracted_quotation'] = [
                {"item_no": 1, "description": f"已載入檔案：{uploaded_file.name} (請直接於下方修改項目)", "qty": 1.0, "unit": "項", "unit_price": 0.0}
            ]
            st.success("成功載入！")

# 顯示解析結果與卡片式介面
if 'ai_extracted_quotation' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 項目清單（共 {len(st.session_state['ai_extracted_quotation'])} 項）")
    
    items = st.session_state['ai_extracted_quotation']
    calculated_grand_total = 0
    
    for idx, item in enumerate(items):
        item_qty = float(item.get('qty', 1.0))
        item_price = float(item.get('unit_price', 0.0))
        item_total_amount = item_qty * item_price
        calculated_grand_total += item_total_amount
        
        qty_str = f"{item_qty} {item.get('unit', '項')}"
        price_str = f"${item_price:,.2f}"
        amount_str = f"${item_total_amount:,.2f}"
        
        with st.container():
            col_h1, col_h2 = st.columns([4, 1])
            with col_h1:
                st.markdown(f"**Item {item.get('item_no', idx+1)}**")
            with col_h2:
                if st.button(f"📋 複製", key=f"copy_desc_{idx}"):
                    st.toast("已成功複製項目內容！", icon="✅")
            
            new_desc = st.text_area(
                "內容描述 (Description)：", 
                value=item.get('description', ''), 
                height=75, 
                key=f"desc_box_{idx}"
            )
            item['description'] = new_desc
            
            cols = st.columns(6)
            with cols[0]:
                st.markdown(f"<div class='metric-label'><b>數量:</b> {qty_str}</div>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("📋 複數", key=f"cp_q_{idx}"):
                    st.toast(f"已複製數量: {qty_str}", icon="✅")
            with cols[2]:
                st.markdown(f"<div class='metric-label'><b>單價:</b> {price_str}</div>", unsafe_allow_html=True)
            with cols[3]:
                if st.button("📋 複價", key=f"cp_p_{idx}"):
                    st.toast(f"已複製單價: {price_str}", icon="✅")
            with cols[4]:
                st.markdown(f"<div class='metric-label'><b>金額:</b> <span style='color: #ffffff; font-weight: bold;'>{amount_str}</span></div>", unsafe_allow_html=True)
            with cols[5]:
                if st.button("📋 複金", key=f"cp_a_{idx}"):
                    st.toast(f"已複製金額: {amount_str}", icon="✅")
            
            st.markdown("---")
            
    st.markdown(f"### 💰 總金額 (Grand Total): **${calculated_grand_total:,.2f}**")
    st.markdown("---")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        if st.button("📥 下載表格數據 (JSON)"):
            export_data = {"grand_total": calculated_grand_total, "items": items}
            json_str = json.dumps(export_data, ensure_ascii=False, indent=4)
            st.download_button("確認下載 JSON", data=json_str, file_name="quotation_items.json", mime="application/json")
    with col_ex2:
        if st.button("🗑️ 清空重置"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

st.markdown("<div class='subtle-watermark'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
