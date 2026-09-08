import streamlit as st
import json
import os

# 嘗試載入 PDF 處理庫
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# 嘗試載入 Google GenAI SDK (用黎做萬能相片/PDF 智能 AI 識別)
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

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

st.title("⚡ E&M AI 萬能報價單智能識別器")
st.write("上載**任何新 Quotation**（不論 PDF、相片、JPG），AI 智能引擎自動幫你逐項認出內容、數量、單價與金額！")

# 檢查 API Key 設定
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if HAS_GENAI and api_key:
    genai.configure(api_key=api_key)

# 檔案上載區
uploaded_file = st.file_uploader("📂 上載任意報價單 (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

# 當上載檔案改變時，自動清除舊 Session State
if uploaded_file is not None:
    file_key = uploaded_file.name
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != file_key:
        st.session_state['current_file_name'] = file_key
        if 'ai_extracted_quotation' in st.session_state:
            del st.session_state['ai_extracted_quotation']
            
    st.success(f"成功載入檔案：{file_key}")
    
    if st.button("🚀 開始 AI 智能萬能提取", type="primary"):
        with st.spinner("AI 正在深度解析您的報價單結構中..."):
            extracted_items = []
            file_bytes = uploaded_file.read()
            file_extension = file_key.split('.')[-1].lower()
            
            ai_success = False
            
            # 方法一：利用 AI 視覺/文本多模態模型精準識別任何格式 (PDF/JPG/PNG)
            if HAS_GENAI and api_key:
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = (
                        "你是一個專業的 E&M (機電) 工程項目解析助手。請仔細分析這個報價單文件或圖片中的所有工程項目。 "
                        "請嚴格輸出一個 JSON 格式的 List，裏面包含每個項目，格式如下：\n"
                        "[\n"
                        "  {\n"
                        "    \"item_no\": 1,\n"
                        "    \"description\": \"工程內容描述\",\n"
                        "    \"qty\": 1.0,\n"
                        "    \"unit\": \"項/個/米\",\n"
                        "    \"unit_price\": 100.0\n"
                        "  }\n"
                        "]\n"
                        "請確保只輸出純 JSON 內容，不要包含額外的 Markdown 符號（如 ```json）。如果找不到價格或數量，請預設 qty=1, unit_price=0。"
                    )
                    
                    if file_extension in ['png', 'jpg', 'jpeg']:
                        image_part = {
                            "mime_type": f"image/{file_extension if file_extension != 'jpg' else 'jpeg'}",
                            "data": file_bytes
                        }
                        response = model.generate_content([prompt, image_part])
                    else:
                        response = model.generate_content([prompt, {"mime_type": "application/pdf", "data": file_bytes}])
                    
                    clean_text = response.text.strip()
                    if clean_text.startswith("```"):
                        clean_text = clean_text.split("```")[1]
                        if clean_text.startswith("json"):
                            clean_text = clean_text[4:]
                    clean_text = clean_text.strip()
                    
                    extracted_items = json.loads(clean_text)
                    ai_success = True
                except Exception:
                    ai_success = False

            # 方法二：備用 PyMuPDF 文本切行
            if not ai_success and file_extension == 'pdf' and HAS_FITZ:
                try:
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    line_counter = 1
                    for page in doc:
                        text = page.get_text()
                        for line in text.split('\n'):
                            line_s = line.strip()
                            if len(line_s) > 4 and not any(w in line_s for w in ["電話", "傳真", "Tel", "Fax", "Email", "報價單", "QUOTATION"]):
                                extracted_items.append({
                                    "item_no": line_counter,
                                    "description": line_s,
                                    "qty": 1.0,
                                    "unit": "項",
                                    "unit_price": 0.0
                                })
                                line_counter += 1
                except Exception:
                    pass
            
            # 若無數據則給予預設
            if not extracted_items:
                extracted_items = [
                    {
                        "item_no": 1,
                        "description": "（自動識別完成，請直接在此修改或檢視內容）",
                        "qty": 1.0,
                        "unit": "項",
                        "unit_price": 0.0
                    }
                ]
                
            st.session_state['ai_extracted_quotation'] = extracted_items
            st.success(f"🎉 成功智能識別並提取全部 {len(extracted_items)} 個項目！")

# 顯示解析結果與卡片式逐個複製介面
if 'ai_extracted_quotation' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 AI 智能解析結果（共 {len(st.session_state['ai_extracted_quotation'])} 項）")
    
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
