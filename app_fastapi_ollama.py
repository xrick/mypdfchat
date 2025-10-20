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

# 設置靜態文件和模板（使用與此文件同層的相對路徑）
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

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

# 嵌入模型初始化說明（僅供閱讀，避免被 Streamlit Magic 輸出）
# 預設使用較小且常用的模型（英文通用）：all-MiniLM-L6-v2
# 若載入失敗，將嘗試備援（中文向量模型）：jinaai/jina-embeddings-v2-base-zh
# 可用環境變數指定本地路徑或其他模型ID：
#   export EMBEDDING_MODEL=/path/to/local/model
# 或
#   export EMBEDDING_MODEL=all-MiniLM-L6-v2
embedding_model_env = os.getenv("EMBEDDING_MODEL")
fallback_model_env = os.getenv("EMBEDDING_FALLBACK")
# 預設使用較小且普及的模型，降低逾時風險。
model_name = (embedding_model_env or "all-MiniLM-L6-v2").strip()
fallback_model = (fallback_model_env or "jinaai/jina-embeddings-v2-base-zh").strip()

model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": False}

_hf_embedder = None  # lazy singleton

def _init_embeddings(name: str):
    logger.info(f"Using embedding model: {name}")
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
        logger.warning(
            "Failed to load embedding model '%s': %s. Trying fallback '%s'...",
            model_name,
            str(e),
            fallback_model,
        )
        try:
            _hf_embedder = _init_embeddings(fallback_model)
        except Exception as e2:
            logger.error(
                "Failed to load fallback embedding model '%s': %s",
                fallback_model,
                str(e2),
            )
            raise RuntimeError(
                "Could not load embedding models. Set EMBEDDING_MODEL to a local path "
                "or ensure network access to Hugging Face Hub."
            ) from e2
    return _hf_embedder

# 全局變量
vectors_store = {}
qa_chains = {}

# 處理文檔嵌入
async def store_doc_embeds(file_content, filename):
    reader = PdfReader(file_content)
    corpus = ''.join([p.extract_text() for p in reader.pages if p.extract_text()])
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(corpus)
    
    # 使用HuggingFace嵌入替代OpenAI嵌入（延遲初始化嵌入器）
    vectors = FAISS.from_texts(chunks, get_embedder())
    
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
    # 直接以 Python 執行本檔時，只有在顯式同意的情況下才啟動 Uvicorn，避免在非主執行緒（例如被 Streamlit 誤執行）發生 signal 錯誤。
    if os.getenv("RUN_UVICORN") == "1":
        port = int(os.getenv("PORT", "8000"))
        reload = os.getenv("UVICORN_RELOAD", "1") in {"1", "true", "True"}
        uvicorn.run("app_fastapi_ollama:app", host="0.0.0.0", port=port, reload=reload)
    else:
        logger.warning(
            "此檔案為 FastAPI 應用，請使用：uvicorn app_fastapi_ollama:app --reload"
        )
