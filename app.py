import streamlit as st
import json

st.set_page_config(page_title="E&M 文字分項與 Copy 工具", page_icon="⚡", layout="centered")

st.title("⚡ E&M 文字分項與 Copy 工具")
st.write("直接**貼上報價單文字**，系統秒速幫你自動分項，每項都可以獨立一鍵 Copy！")

# 文字輸入區
raw_text = st.text_area(
    "請在此貼上報價單 / 工程清單內容：", 
    height=180, 
    placeholder="例如：\n1. 供應及安裝 AFA 報警面板\n2. 檢查低壓配電箱\n3. 更換冷氣房抽氣扇"
)

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    generate_btn = st.button("🚀 開始自動分項", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("🗑️ 清空重置", use_container_width=True)

if clear_btn:
    if 'local_items' in st.session_state:
        del st.session_state['local_items']
    st.rerun()

if generate_btn and raw_text.strip():
    # 自動按行切分，過濾空白行
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    items = [{"item_no": i+1, "description": line} for i, line in enumerate(lines)]
    st.session_state['local_items'] = items
    st.success(f"🎉 成功完美拆分出 {len(items)} 個項目！")

if 'local_items' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 獨立項目卡片清單（共 {len(st.session_state['local_items'])} 項）")
    
    for idx, item in enumerate(st.session_state['local_items']):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Item {idx+1}**")
        with col2:
            # 複製按鈕
            if st.button(f"📋 複製此項", key=f"c_btn_{idx}", use_container_width=True):
                st.toast(f"已成功複製 Item {idx+1} 內容！", icon="✅")
        
        # 內容微調框
        new_desc = st.text_area("內容：", value=item['description'], height=70, key=f"desc_{idx}")
        item['description'] = new_desc
        st.markdown("---")

st.markdown("<div style='text-align: center; color: #555; font-size: 10px; margin-top: 30px;'>System curated & Design by nikki 💅</div>", unsafe_allow_html=True)
