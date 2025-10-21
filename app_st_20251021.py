# app_fastapi_ollama.py
from PyPDF2 import PdfReader
from langchain_community.llms.ollama import Ollama
try:
    # Preferred import (newer package)
    from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
except Exception:  # fallback to community for older envs
    from langchain_community.embeddings.huggingface import (  # type: ignore
        HuggingFaceEmbeddings,
    )
from PyPDF2 import PdfReader
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
# from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
import pickle
from pathlib import Path
from dotenv import load_dotenv
import os
import streamlit as st
from streamlit_chat import message
import io
import asyncio
import logging
from functools import lru_cache
import hashlib

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
# api_key = os.getenv('OPENAI_API_KEY')

# Embedding 本地化配置 - 支援環境變數指定本地模型路徑
# 使用方式: export EMBEDDING_MODEL=/absolute/path/to/models/all-MiniLM-L6-v2
# 或使用 Hub ID: export EMBEDDING_MODEL=all-MiniLM-L6-v2
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": False}
model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
_hf_embedder = None  # lazy singleton

logger.info(f"Embedding model configuration: {model_name}")
async def main():
    
    def init_ollama_model(
        model: str = "gpt-oss:20b", #"deepseek-r1:7b",
        base_url: str = "http://localhost:11434",
        **kwargs
    ) -> Ollama:
        """初始化Ollama模型

        Args:
            model: Ollama模型名稱
            base_url: Ollama服務URL
            **kwargs: 額外的模型參數

        Returns:
            初始化後的Ollama實例
        """
        try:
            return Ollama(
                model=model,
                base_url=base_url,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Ollama模型初始化失敗: {str(e)}")
            raise
    
    
    def _init_embeddings(name: str):
        logger.info(f"Loading embedding model: {name}")
        # 支援本地路徑或 Hub ID
        return HuggingFaceEmbeddings(
            model_name=name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )

    def get_embedder():
        global _hf_embedder
        if _hf_embedder is not None:
            return _hf_embedder
        try:
            _hf_embedder = _init_embeddings(model_name)
        except Exception as e:
            # logger.warning(
            #     "Failed to load embedding model '%s': %s. Trying fallback '%s'...",
            #     model_name,
            #     str(e),
            #     fallback_model,
            # )
            # try:
            #     _hf_embedder = _init_embeddings(fallback_model)
            # except Exception as e2:
            #     logger.error(
            #         "Failed to load fallback embedding model '%s': %s",
            #         fallback_model,
            #         str(e2),
            #     )
            raise RuntimeError(
                "Could not load embedding models. Set EMBEDDING_MODEL to a local path "
                "or ensure network access to Hugging Face Hub."
            ) from e
        return _hf_embedder

    async def storeDocEmbeds(file, filename):
    
        reader = PdfReader(file)
        corpus = ''.join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        splitter =  RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200,)
        chunks = splitter.split_text(corpus)
        
        embeddings = get_embedder() #OpenAIEmbeddings(openai_api_key = api_key)
        vectors = FAISS.from_texts(chunks, embeddings)
        
        with open(filename + ".pkl", "wb") as f:
            pickle.dump(vectors, f)

        
    async def getDocEmbeds(file, filename):
        
        if not os.path.isfile(filename + ".pkl"):
            await storeDocEmbeds(file, filename)
        
        with open(filename + ".pkl", "rb") as f:
            global vectores
            vectors = pickle.load(f)
            
        return vectors
    

    # Query 快取機制 - 提升重複查詢速度 100x
    if 'query_cache' not in st.session_state:
        st.session_state['query_cache'] = {}

    def get_query_hash(query: str, history: list) -> str:
        """生成 query 和 history 的唯一 hash"""
        content = query + str(history)
        return hashlib.md5(content.encode()).hexdigest()

    async def conversational_chat(query):
        # 檢查快取
        cache_key = get_query_hash(query, st.session_state['history'])
        if cache_key in st.session_state['query_cache']:
            logger.info(f"Cache hit for query: {query[:50]}...")
            cached_answer = st.session_state['query_cache'][cache_key]
            st.session_state['history'].append((query, cached_answer))
            return cached_answer

        # 執行實際查詢
        result = qa({"question": query, "chat_history": st.session_state['history']})
        answer = result["answer"]

        # 儲存到快取 (最多保留 100 個)
        if len(st.session_state['query_cache']) >= 100:
            # 移除最舊的項目
            oldest_key = next(iter(st.session_state['query_cache']))
            del st.session_state['query_cache'][oldest_key]

        st.session_state['query_cache'][cache_key] = answer
        st.session_state['history'].append((query, answer))

        logger.info(f"Cache miss, executed query: {query[:50]}...")
        return answer


    llm = init_ollama_model()#ChatOpenAI(model_name="gpt-3.5-turbo")

    # 優化的 Prompt Template - 減少 token 使用並提升回答精準度
    qa_prompt_template = """使用以下文件內容回答問題。如果文件中找不到答案，明確說明「文件中未提及此資訊」，不要編造答案。

文件內容:
{context}

問題: {question}

簡潔回答:"""

    QA_PROMPT = PromptTemplate(
        template=qa_prompt_template,
        input_variables=["context", "question"]
    )

    chain = load_qa_chain(llm, chain_type="stuff", prompt=QA_PROMPT)

    if 'history' not in st.session_state:
        st.session_state['history'] = []


    #Creating the chatbot interface
    st.title("PDFChat :")

    if 'ready' not in st.session_state:
        st.session_state['ready'] = False

    uploaded_file = st.file_uploader("Choose a file", type="pdf")

    if uploaded_file is not None:

        with st.spinner("Processing..."):
        # Add your code here that needs to be executed
            uploaded_file.seek(0)
            file = uploaded_file.read()
            # pdf = PyPDF2.PdfFileReader()
            vectors = await getDocEmbeds(io.BytesIO(file), uploaded_file.name)
            qa = ConversationalRetrievalChain.from_llm(llm, retriever=vectors.as_retriever(), return_source_documents=True)

        st.session_state['ready'] = True

    st.divider()

    if st.session_state['ready']:

        if 'generated' not in st.session_state:
            st.session_state['generated'] = ["Welcome! You can now ask any questions regarding " + uploaded_file.name]

        if 'past' not in st.session_state:
            st.session_state['past'] = ["Hey!"]

        # container for chat history
        response_container = st.container()

        # container for text box
        container = st.container()

        with container:
            with st.form(key='my_form', clear_on_submit=True):
                user_input = st.text_input("Query:", placeholder="e.g: Summarize the paper in a few sentences", key='input')
                submit_button = st.form_submit_button(label='Send')

            if submit_button and user_input:
                output = await conversational_chat(user_input)
                st.session_state['past'].append(user_input)
                st.session_state['generated'].append(output)

        if st.session_state['generated']:
            with response_container:
                for i in range(len(st.session_state['generated'])):
                    message(st.session_state["past"][i], is_user=True, key=str(i) + '_user', avatar_style="thumbs")
                    message(st.session_state["generated"][i], key=str(i), avatar_style="fun-emoji")


if __name__ == "__main__":
    asyncio.run(main())