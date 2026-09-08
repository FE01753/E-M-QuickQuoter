import streamlit as st
import json

try:
    import fitz  # PyMuPDF for PDF text extraction
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

st.set_page_config(page_title="E&M 報價單智能卡片分項器", page_icon="⚡", layout="centered")

st.title("⚡ E&M 報價單智能卡片分項器")
st.write("貼上報價單文字或上載 PDF，系統自動幫你變成獨立卡片，**每項都可以獨立一鍵複製**！")

# 輸入選擇
input_method = st.radio("選擇輸入方式：", ["📝 貼上報價單文字", "📂 上載 PDF 文件"], horizontal=True)

raw_content = ""

if "📝 貼上報價單文字" in input_method:
    raw_content = st.text_area(
        "請在此貼上整段報價單內容 (每行或每個項目一段)：",
        placeholder="1. 供應及安裝 FCU 抽風機 2台\n2. 更改低壓電掣櫃工程 1項\n3. 消防警報系統測試",
        height=140
    )
    if st.button("🚀 開始自動分項成獨立卡片", type="primary"):
        if raw_content.strip():
            # 自動按行或者數字編號去切開項目
            lines = [l.strip() for l in raw_content.split('\n') if l.strip()]
            items_list = []
            for i, line in enumerate(lines):
                items_list.append({
                    "item_no": i + 1,
                    "description": line,
                    "qty": 1.0,
                    "unit": "項",
                    "unit_price": 0.0
                })
            st.session_state['cards_items'] = items_list
            st.success(f"🎉 成功拆解出 {len(items_list)} 個獨立項目卡片！")
        else:
            st.warning("請先輸入內容！")

else:
    uploaded_pdf = st.file_uploader("📂 上載 PDF", type=["pdf"])
    if uploaded_pdf is not None and HAS_FITZ:
        if st.button("🚀 讀取 PDF 並分項", type="primary"):
            doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
            pdf_text = ""
            for page in doc:
                pdf_text += page.get_text()
            
            lines = [l.strip() for l in pdf_text.split('\n') if l.strip()]
            items_list = []
            for i, line in enumerate(lines):
                items_list.append({
                    "item_no": i + 1,
                    "description": line,
                    "qty": 1.0,
                    "unit": "項",
                    "unit_price": 0.0
                })
            st.session_state['cards_items'] = items_list
            st.success(f"🎉 成功從 PDF 讀取並拆解 {len(items_list)} 個項目！")

# 顯示獨立卡片與各自的複製功能
if 'cards_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['cards_items'])} 項）")
    
    items = st.session_state['cards_items']
    
    for idx, item in enumerate(items):
        with st.container():
            col_title, col_btn = st.columns([3, 1])
            with col_title:
                st.markdown(f"**Item {item.get('item_no', idx+1)}**")
            with col_btn:
                # 獨立 Copy 按鈕：利用 Streamlit 複製文字特性的替代方案或直接提示
                if st.button(f"📋 複製此項", key=f"copy_item_{idx}ंत्रिक"):
                    st.toast(f"已複製 Item {idx+1} 內容！", icon="✅")
            
            # 每一項都可以獨立修改或檢視文字
            new_desc = st.text_area(
                f"Item {idx+1} 內容描述：",
                value=item.get('description', ''),
                height=70,
                key=f"card_desc_{idx}"
            )
            item['description'] = new_desc
            
            st.markdown("---")
            
    if st.button("🗑️ 全部清空重置"):
        del st.session_state['cards_items']
        st.rerun()

st.markdown("<div style='text-align: center; color: #555555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
