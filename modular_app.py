import streamlit as st
import os

# --- 頁面設定 ---
st.set_page_config(page_title="Modular RAG PDF Chatbot", layout="wide")
st.title("📄 Modular RAG PDF Chatbot (Parent-Child Strategy)")
st.markdown("""
    Welcome! This chatbot is powered by a modular RAG architecture using the Parent-Child chunking strategy. 
    Upload your PDF and start asking questions.
""")

# --- 初始化 Session 狀態 ---
# 用於儲存 RAG 鏈
if "llm_chain" not in st.session_state:
    st.session_state.llm_chain = None
# 用於儲存聊天歷史紀錄
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 顯示歷史訊息 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 側邊欄 UI ---
with st.sidebar:
    st.header("Upload Your PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        if st.button("Process PDF"):
            # 在後續步驟中，我們將在此處添加 PDF 處理邏輯
            with st.spinner("Processing PDF... (logic not implemented yet)"):
                st.success(f"File '{uploaded_file.name}' uploaded! Processing logic will be added in the next steps.")
    else:
        st.warning("Please upload a PDF file to begin.")

# --- 主聊天介面 ---
if prompt_input := st.chat_input("Ask a question about the PDF..."):
    st.session_state.messages.append({"role": "user", "content": prompt_input})
    with st.chat_message("user"):
        st.markdown(prompt_input)

    with st.chat_message("assistant"):
        # 在後續步驟中，我們將在此處添加模型回應邏輯
        st.markdown("Thinking... (response logic not implemented yet)")
        # st.session_state.messages.append({"role": "assistant", "content": assistant_response})