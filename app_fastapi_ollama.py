# app_fastapi_ollama.py
from PyPDF2 import PdfReader
from langchain_community.llms.ollama import Ollama
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import pickle
from pathlib import Path
from dotenv import load_dotenv
import os
import io
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI應用
app = FastAPI(title="PDF Chat API")

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設置靜態文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 加載環境變量
load_dotenv()

# 初始化Ollama模型
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

# 初始化嵌入模型
embedding_path = "/home/mapleleaf/LCJRepos/Embedding_Models/jina-embeddings-v2-base-zh"
model_name = embedding_path
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': False}
hf = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# 全局變量
vectors_store = {}
qa_chains = {}

# 處理文檔嵌入
async def store_doc_embeds(file_content, filename):
    reader = PdfReader(file_content)
    corpus = ''.join([p.extract_text() for p in reader.pages if p.extract_text()])
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(corpus)
    
    # 使用HuggingFace嵌入替代OpenAI嵌入
    vectors = FAISS.from_texts(chunks, hf)
    
    # 保存向量存儲
    vectors_store[filename] = vectors
    return vectors

async def get_doc_embeds(file_content, filename):
    if filename not in vectors_store:
        vectors = await store_doc_embeds(file_content, filename)
    else:
        vectors = vectors_store[filename]
    return vectors

async def conversational_chat(query, filename, history):
    if filename not in qa_chains:
        return {"error": "請先上傳PDF文件"}

    chain_data = qa_chains[filename]
    llm = chain_data["llm"]
    retriever = chain_data["retriever"]

    # 檢索相關文檔
    docs = retriever.get_relevant_documents(query)
    context = "\n\n".join([doc.page_content for doc in docs])

    # 構建包含歷史的提示
    history_text = "\n".join([f"Human: {q}\nAssistant: {a}" for q, a in history])

    # 生成回答
    prompt = f"""根據以下上下文回答問題。如果上下文中沒有相關信息,請說明你不知道。

歷史對話:
{history_text}

上下文:
{context}

問題: {query}

回答:"""

    answer = llm.invoke(prompt)
    history.append((query, answer))
    return {"answer": answer, "history": history}

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        vectors = await get_doc_embeds(io.BytesIO(file_content), file.filename)

        # 使用Ollama模型替代ChatOpenAI
        llm = init_ollama_model()
        retriever = vectors.as_retriever()

        # 儲存 LLM 和 retriever
        qa_chains[file.filename] = {
            "llm": llm,
            "retriever": retriever
        }

        return JSONResponse(content={"status": "success", "filename": file.filename})
    except Exception as e:
        logger.error(f"上傳PDF時出錯: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/chat/")
async def chat(
    query: str = Form(...),
    filename: str = Form(...),
    history: str = Form("[]")
):
    try:
        # 將歷史記錄從字符串轉換為列表
        import json
        history_list = json.loads(history)
        
        result = await conversational_chat(query, filename, history_list)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"聊天時出錯: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("app_fastapi_ollama:app", host="0.0.0.0", port=8000, reload=True)
