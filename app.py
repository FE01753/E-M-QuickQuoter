import streamlit as st
import pandas as pd
import json

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 萬能報價單極速編輯器", page_icon="⚡", layout="centered")

st.title("⚡ E&M 萬能報價單極速編輯器 (Universal Table Editor)")
st.write("上載**任何** PDF 報價單：文字版自動提取，掃描版可直接喺下方互動表格自由增刪修改、實時計數！")

uploaded_file = st.file_uploader("📂 上載任意報價單 PDF 或掃描檔案", type=["pdf", "png", "jpg", "jpeg"])

# 初始化 Session State 中的表格數據
if 'df_items' not in st.session_state:
    st.session_state['df_items'] = pd.DataFrame(columns=["Item", "Description", "Qty", "Unit", "UnitPrice"])

if uploaded_file is not None:
    file_key = uploaded_file.name
    if 'last_file' not in st.session_state or st.session_state['last_file'] != file_key:
        st.session_state['last_file'] = file_key
        
        extracted = []
        # 嘗試自動讀取文字 PDF
        if file_key.lower().endswith('.pdf') and HAS_FITZ:
            try:
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for page in doc:
                    text = page.get_text()
                    for line in text.split('\n'):
                        line_s = line.strip()
                        if len(line_s) > 4 and not any(w in line_s for w in ["電話", "傳真", "報價單", "QUOTATION", "施工地點"]):
                            extracted.append(line_s)
            except Exception:
                pass
        
        # 如果成功抽到文字就自動填入，如果係純掃描檔就給予乾淨表格讓用戶自由輸入
        if extracted:
            data = []
            for idx, text in enumerate(extracted[:15], 1):
                data.append({"Item": idx, "Description": text, "Qty": 1.0, "Unit": "項", "UnitPrice": 0.0})
            st.session_state['df_items'] = pd.DataFrame(data)
            st.success(f"🎉 成功自動提取 {len(data)} 行文字內容！")
        else:
            st.session_state['df_items'] = pd.DataFrame([
                {"Item": 1, "Description": "（此為掃描檔，請直接在下方表格修改或點擊 '+' 增加行數）", "Qty": 1.0, "Unit": "項", "UnitPrice": 0.0}
            ])
            st.warning("⚠️ 檔案屬圖片掃描檔，已解鎖互動表格，您可以直接在下方自由輸入或貼上任何新單內容！")

# 互動式 Excel 級別編輯器（支援任意新增、刪除、修改行）
st.markdown("---")
st.subheader("📋 報價單項目互動控制台")
st.markdown("💡 *提示：你可以直接在表格內修改文字、更改數量與單價，亦可以按底部的 **'+ 按鈕'** 隨意新增無限行！*")

edited_df = st.data_editor(
    st.session_state['df_items'],
    num_rows="dynamic",
    use_container_width=True,
    key="universal_quotation_editor",
    column_config={
        "Item": st.column_config.NumberColumn("項號", width="small"),
        "Description": st.column_config.TextColumn("工程內容描述 (Description)", width="large"),
        "Qty": st.column_config.NumberColumn("數量", min_value=0.0, format="%.1f"),
        "Unit": st.column_config.TextColumn("單位", width="small"),
        "UnitPrice": st.column_config.NumberColumn("單價 ($)", min_value=0.0, format="%.2f"),
    }
)

# 實時計算總金額
if not edited_df.empty and 'Qty' in edited_df.columns and 'UnitPrice' in edited_df.columns:
    edited_df['Amount'] = edited_df['Qty'] * edited_df['UnitPrice']
    grand_total = edited_df['Amount'].sum()
    
    st.markdown("---")
    st.markdown(f"### 💰 實時總金額 (Grand Total): **${grand_total:,.2f}**")
    st.markdown("---")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button("📥 下載表格數據 (JSON)"):
            json_str = edited_df.to_json(orient="records", force_ascii=False)
            st.download_button("確認下載 JSON", data=json_str, file_name="universal_quotation.json", mime="application/json")
    with col_e2:
        if st.button("🗑️ 清空全部重置"):
            st.session_state['df_items'] = pd.DataFrame(columns=["Item", "Description", "Qty", "Unit", "UnitPrice"])
            if 'last_file' in st.session_state:
                del st.session_state['last_file']
            st.rerun()

st.markdown("<div style='text-align: center; color: #55; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
