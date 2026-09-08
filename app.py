import streamlit as st
import json
import os

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

st.set_page_config(page_title="E&M AI 萬能報價單智能識別器", page_icon="⚡", layout="centered")

st.title("⚡ E&M AI 萬能報價單智能識別器")
st.write("上載任何新 Quotation（PDF、相片、JPG），AI 自動幫你逐項認出內容、數量與金額！")

# 檢查 API Key (支援 Secrets 或網頁端手動輸入)
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

if not api_key and HAS_GENAI:
    with st.sidebar:
        st.subheader("🔑 API 設定")
        user_input_key = st.text_input("請輸入 Gemini API Key:", type="password")
        if user_input_key:
            api_key = user_input_key

if HAS_GENAI and api_key:
    genai.configure(api_key=api_key)

uploaded_file = st.file_uploader("📂 上載任意報價單 (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_key = uploaded_file.name
    if 'current_file_name' not in st.session_state or st.session_state['current_file_name'] != file_key:
        st.session_state['current_file_name'] = file_key
        if 'ai_extracted_quotation' in st.session_state:
            del st.session_state['ai_extracted_quotation']
            
    st.success(f"成功載入檔案：{file_key}")
    
    if st.button("🚀 開始 AI 智能萬能提取", type="primary"):
        if not api_key:
            st.error("⚠️ 請先在側邊欄 (Sidebar) 輸入你的 Gemini API Key，或於 Streamlit Secrets 設定！")
        else:
            with st.spinner("AI 正在深度解析您的報價單結構中..."):
                extracted_items = []
                file_bytes = uploaded_file.read()
                file_extension = file_key.split('.')[-1].lower()
                
                ai_success = False
                try:
                    # 使用標準 gemini-1.5-flash 模型進行多模態識別
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = (
                        "你是一個專業的 E&M (機電) 工程項目解析助手。請仔細分析這個報價單圖片或文件中的所有工程項目。 "
                        "請嚴格輸出一個純 JSON 格式的 List（不要包含任何 markdown 符號如 ```json 或其他文字），裏面包含每個項目，格式如下：\n"
                        "[\n"
                        "  {\n"
                        "    \"item_no\": 1,\n"
                        "    \"description\": \"工程內容描述\",\n"
                        "    \"qty\": 1.0,\n"
                        "    \"unit\": \"項/個/米/台\",\n"
                        "    \"unit_price\": 100.0\n"
                        "  }\n"
                        "]\n"
                        "如果找不到價格或數量，請預設 qty=1, unit_price=0。"
                    )
                    
                    if file_extension in ['png', 'jpg', 'jpeg']:
                        image_part = {
                            "mime_type": f"image/{file_extension if file_extension != 'jpg' else 'jpeg'}",
                            "data": file_bytes
                        }
                        response = model.generate_content([prompt, image_part])
                    elif file_extension == 'pdf':
                        response = model.generate_content([prompt, {"mime_type": "application/pdf", "data": file_bytes}])
                    
                    clean_text = response.text.strip()
                    if clean_text.startswith("```"):
                        clean_text = clean_text.split("```")[1]
                        if clean_text.startswith("json"):
                            clean_text = clean_text[4:]
                    clean_text = clean_text.strip()
                    
                    extracted_items = json.loads(clean_text)
                    ai_success = True
                except Exception as e:
                    st.error(f"AI 識別出錯詳情: {str(e)}")
                    ai_success = False

                if ai_success and extracted_items:
                    st.session_state['ai_extracted_quotation'] = extracted_items
                    st.success(f"🎉 AI 成功智能識別並提取全部 {len(extracted_items)} 個項目！")
                else:
                    st.warning("⚠️ AI 未能成功解析，請檢查相片清晰度或 API Key 是否正確。")

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
                if st.button(f"📋 複製內容", key=f"copy_desc_{idx}"):
                    st.toast("已成功複製項目內容！", icon="✅")
            
            new_desc = st.text_area(
                "內容描述 (Description)：", 
                value=item.get('description', ''), 
                height=85, 
                key=f"desc_box_{idx}"
            )
            item['description'] = new_desc
            
            cols = st.columns(6)
            with cols[0]:
                st.markdown(f"<div style='font-size:13px; color:#d0d0d0;'><b>數量:</b> {qty_str}</div>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("📋 複數", key=f"cp_q_{idx}"):
                    st.toast(f"已複製數量: {qty_str}", icon="✅")
            with cols[2]:
                st.markdown(f"<div style='font-size:13px; color:#d0d0d0;'><b>單價:</b> {price_str}</div>", unsafe_allow_html=True)
            with cols[3]:
                if st.button("📋 複價", key=f"cp_p_{idx}"):
                    st.toast(f"已複製單價: {price_str}", icon="✅")
            with cols[4]:
                st.markdown(f"<div style='font-size:13px; color:#d0d0d0;'><b>金額:</b> <span style='color: #fff; font-weight: bold;'>{amount_str}</span></div>", unsafe_allow_html=True)
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
            st.download_button("確認下載 JSON", data=json_str, file_name="ai_extracted_quotation.json", mime="application/json")
    with col_ex2:
        if st.button("🗑️ 清空重置（上載新單）"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

st.markdown("<div style='text-align: center; color: #555555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
