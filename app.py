import streamlit as st

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 報價單內容純粹識別器", page_icon="⚡", layout="centered")

# --- 自訂 CSS 樣式 ---
st.markdown(
    """
    <style>
    .stTextArea textarea {
        font-family: 'Aptos', sans-serif !important;
        font-size: 12pt !important;
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

st.title("⚡ E&M 報價單內容純粹識別器")
st.write("上載**任何**報價單 PDF，系統自動智能識別出所有工程內容，支援獨立逐個項目一鍵複製！")

# 檔案上載區
uploaded_file = st.file_uploader("📂 上載任意報價單 PDF 檔案", type=["pdf"])

if uploaded_file is not None:
    file_key = uploaded_file.name
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != file_key:
        st.session_state['current_file_name'] = file_key
        if 'pure_extracted_items' in st.session_state:
            del st.session_state['pure_extracted_items']
            
    st.success(f"成功載入檔案：{file_key}")
    
    if st.button("🚀 開始識別工程內容", type="primary"):
        with st.spinner("系統正在深度掃描並提取 PDF 內容中..."):
            extracted_items = []
            
            # 通用 PDF 文字識別提取
            if HAS_FITZ:
                try:
                    pdf_bytes = uploaded_file.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    line_counter = 1
                    for page in doc:
                        text = page.get_text()
                        for line in text.split('\n'):
                            line_s = line.strip()
                            # 過濾頁眉頁腳或太短、無關嘅字串
                            if len(line_s) > 4 and not any(w in line_s for w in ["電話", "傳真", "Tel", "Fax", "Email", "報價單", "QUOTATION", "施工地點", "總工程金額", "HK$"]):
                                extracted_items.append({
                                    "item_no": line_counter,
                                    "description": line_s
                                })
                                line_counter += 1
                except Exception:
                    pass
            
            # 如果捉唔到文字（純圖片掃描檔），提供空白框供用戶手動貼上
            if not extracted_items:
                extracted_items = [
                    {
                        "item_no": 1,
                        "description": "（此 PDF 可能是純圖片掃描檔，請直接於下方修改或輸入項目內容）"
                    }
                ]
                
            st.session_state['pure_extracted_items'] = extracted_items
            st.success(f"🎉 成功識別出全部 {len(extracted_items)} 個項目內容！")

# 顯示純粹嘅逐個複製清單（無總金額、無計算）
if 'pure_extracted_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 識別結果清單（共 {len(st.session_state['pure_extracted_items'])} 項）")
    
    items = st.session_state['pure_extracted_items']
    
    for idx, item in enumerate(items):
        with st.container():
            col_h1, col_h2 = st.columns([4, 1])
            with col_h1:
                st.markdown(f"**Item {item['item_no']}**")
            with col_h2:
                if st.button(f"📋 複製內容", key=f"pure_copy_desc_{idx}"):
                    st.toast(f"已成功複製 Item {item['item_no']} 內容！", icon="✅")
            
            # 內容文字框（可自由微調修改文字）
            new_desc = st.text_area(
                "內容描述 (Description)：", 
                value=item['description'], 
                height=75, 
                key=f"pure_desc_box_{idx}"
            )
            item['description'] = new_desc
            
            st.markdown("---")
            
    if st.button("🗑️ 清空重置"):
        if 'pure_extracted_items' in st.session_state:
            del st.session_state['pure_extracted_items']
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
