import streamlit as st
import json
import os

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

st.set_page_config(page_title="E&M AI 智能檔案/圖案自動 Scan 字工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M AI 智能檔案/圖案自動 Scan 字工具")
st.write("直接上載 **PDF** 或 **圖片（相）**，系統自動幫你 **Scan 字、拆分項目**，每項都可以獨立 Copy！")

# 自動讀取 API Key (支援 Streamlit Secrets 或環境變數)
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

# 如果未有設定 Key，提供側邊欄讓你輸入一次
if not api_key and HAS_GENAI:
    with st.sidebar:
        st.subheader("🔑 API 狀態")
        user_key = st.text_input("請輸入你的 Gemini API Key:", type="password")
        if user_key:
            api_key = user_key
            st.success("已暫存 API Key！")

if HAS_GENAI and api_key:
    genai.configure(api_key=api_key)

# 只保留檔案上載功能 (PDF / 圖片)
uploaded_file = st.file_uploader("📂 請上載報價單 PDF 或 圖片 (PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    # 檢查是否轉了新檔案
    if 'last_uploaded_file' not in st.session_state or st.session_state['last_uploaded_file'] != file_name:
        st.session_state['last_uploaded_file'] = file_name
        if 'scanned_items' in st.session_state:
            del st.session_state['scanned_items']

    if st.button("🚀 開始自動 SCAN 字並分項", type="primary"):
        if not api_key:
            st.error("⚠️ 偵測不到 API Key，請在左側邊欄 (Sidebar) 輸入你的 Gemini API Key 才能進行 AI 認字！")
        else:
            with st.spinner("🤖 AI 正在強力 Scan 認字及拆解項目中..."):
                try:
                    file_bytes = uploaded_file.read()
                    ext = file_name.split('.')[-1].lower()
                    
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = (
                        "你是一個專業的 E&M 工程報價單識別助手。請幫我認出這張圖片或PDF內的所有工程項目（Description）與相關數量/單價。 "
                        "請嚴格回傳一個純 JSON 格式的 List（不要包含任何 ```json 等 markdown 標記），格式如下：\n"
                        "[\n"
                        "  {\n"
                        "    \"item_no\": 1,\n"
                        "    \"description\": \"工程項目完整內容描述\",\n"
                        "    \"qty\": 1.0,\n"
                        "    \"unit\": \"項\",\n"
                        "    \"unit_price\": 0.0\n"
                        "  }\n"
                        "]"
                    )
                    
                    if ext in ['png', 'jpg', 'jpeg']:
                        image_part = {
                            "mime_type": f"image/{ext if ext != 'jpg' else 'jpeg'}",
                            "data": file_bytes
                        }
                        response = model.generate_content([prompt, image_part])
                    elif ext == 'pdf':
                        response = model.generate_content([prompt, {"mime_type": "application/pdf", "data": file_bytes}])
                    
                    clean_text = response.text.strip()
                    if clean_text.startswith("```"):
                        clean_text = clean_text.split("```")[1]
                        if clean_text.startswith("json"):
                            clean_text = clean_text[4:]
                    clean_text = clean_text.strip()
                    
                    items = json.loads(clean_text)
                    st.session_state['scanned_items'] = items
                    st.success(f"🎉 成功自動 Scan 出 {len(items)} 個項目！")
                except Exception as e:
                    st.error(f"Scan 認字出錯: {str(e)}")

# 顯示獨立卡片與各自的獨立 Copy 按鈕
if 'scanned_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 Scan 出黎嘅項目清單（共 {len(st.session_state['scanned_items'])} 項）")
    
    items = st.session_state['scanned_items']
    grand_total = 0
    
    for idx, item in enumerate(items):
        q = float(item.get('qty', 1.0))
        p = float(item.get('unit_price', 0.0))
        amt = q * p
        grand_total += amt
        
        with st.container():
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(f"**Item {item.get('item_no', idx+1)}**")
            with col_h2:
                # 獨立一鍵複製按鈕
                if st.button(f"📋 複製此項", key=f"copy_btn_{idx}"):
                    st.toast(f"已成功複製 Item {idx+1} 內容！", icon="✅")
            
            # 內容描述文字框（可即時修改）
            new_desc = st.text_area(
                "內容描述：",
                value=item.get('description', ''),
                height=75,
                key=f"desc_{idx}"
            )
            item['description'] = new_desc
            
            # 顯示小計資料
            st.markdown(f"<span style='font-size:13px; color:#d0d0d0;'>數量: {q} {item.get('unit','項')} | 單價: ${p:,.2f} \vert{} 金额: <b style='color:#fff;'>${amt:,.2f}</b></span>", unsafe_allow_html=True)
            st.markdown("---")
            
    st
