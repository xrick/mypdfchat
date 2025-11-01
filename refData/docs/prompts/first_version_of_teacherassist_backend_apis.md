好的，作為一名專業的 Web 應用程式開發人員，我將為您逐步拆解並建立（或在此情境下，記錄）一個強健的後端 API，以作為 Presenton 服務的中介層 (BFF - Backend for Frontend)。

這個後端 API 的核心目的是**封裝複雜性**。前端不應該知道 Presenton、Ollama 或 Pexels 的存在；它只應該與這個後端的 API 進行通訊。

我們將依據您提供的專案檔案，逐步完成這項任務。

-----

## 步驟 1：定義資料模型 (Pydantic Models)

在 FastAPI 中，我們不使用標準的 `dataclass`，而是使用 **Pydantic 的 `BaseModel`**。這能為我們的 API 提供強大的資料驗證、解析和文件自動生成 (例如 Swagger UI) 功能。

根據 `backend/app/api/routes.py` 和 `documentation/project_summary_zh.md` 的內容，我們需要定義以下模型。這些模型應存放在 `backend/app/models.py` 檔案中。

```python
# 檔案：backend/app/models.py
#
# 說明：
# 這些 Pydantic 模型定義了 API 端點的請求和回應的資料結構。
# FastAPI 將使用這些模型來自動驗證傳入的 JSON 資料，
# 並將傳出的 Python 物件序列化為 JSON。

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

# --- 內部使用的模型 ---

class TemplateType(str, Enum):
    """
    定義可用的簡報模板樣式。
    .value 會在 API 路由中被使用。
    """
    ADMINISTRATIVE = "administrative"
    EDUCATIONAL = "educational"
    GENERAL = "general"

class SlideContent(BaseModel):
    """
    定義單張投影片的結構。
    這是在 content_processor 中生成並傳遞給 Presenton 的核心資料。
    """
    title: str
    type: str  # 例如：title, overview, content, conclusion
    content: List[str]
    image_query: Optional[str] = None
    image_url: Optional[str] = None

# --- API 請求 (Request) 模型 ---

class GenerateRequest(BaseModel):
    """
    用於 POST /api/generate 端點。
    前端發起簡報生成任務時傳送的資料。
    """
    content: str  # 至少 50 個字元
    template: TemplateType = TemplateType.ADMINISTRATIVE
    language: str = "zh-TW"

class TranscriptRequest(BaseModel):
    """
    用於 POST /api/transcript/generate 端點。
    前端請求生成演講稿時傳送的資料。
    """
    presentation_id: str
    style: str = "educational"  # formal|conversational|educational
    language: str = "zh-TW"


# --- API 回應 (Response) 模型 ---

class GenerateResponse(BaseModel):
    """
    POST /api/generate 的初始回應。
    立即回傳一個任務 ID，以便前端開始輪詢進度。
    """
    task_id: str
    status: str
    progress: int
    message: str

class ProgressResponse(BaseModel):
    """
    GET /api/progress/{task_id} 的回應。
    回傳任務的目前狀態。
    """
    task_id: str
    status: str  # processing | completed | failed
    progress: int
    current_step: str
    message: str
    presentation: Optional[Dict[str, Any]] = None  # 在 'completed' 時填充
    presentation_id: Optional[str] = None      # 在 'completed' 時填充

class TranscriptResponse(BaseModel):
    """
    POST /api/transcript/generate 的回應。
    回傳完整的演講稿資料。
    """
    presentation_id: str
    total_slides: int
    total_duration_minutes: int
    transcripts: List[Dict[str, Any]]
    full_transcript: str
```

-----

## 步驟 2：後端 API 端點 (含專業文件)

以下是 `backend/app/api/routes.py` 的內容，我已為每個函式**加入了詳盡的 docstring (文件註解)**，說明了參數 (Goal 2a) 和它呼叫的相關服務 (Goal 2b)。

```python
# 檔案：backend/app/api/routes.py
#
# 說明：
# 這是 FastAPI 的核心路由檔案。
# 它定義了前端可以呼叫的所有 API 端點。
# 這個中介層 (BFF) 負責協調後續的服務，
# 例如 content_processor、presenton_service 和 zephyr_service。

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import uuid
import os
from app.models import (
    GenerateRequest, GenerateResponse, ProgressResponse, 
    TranscriptRequest, TranscriptResponse
)
from app.services.content_processor import content_processor
from app.services.presenton_service import PresentonService
from app.services.zephyr_service import ZephyrService
from app.config import get_settings

router = APIRouter()
settings = get_settings()
presenton = PresentonService()
zephyr = ZephyrService()

# 記憶體內快取，用於儲存演講稿
# 注意：在生產環境中，這應替換為 Redis 或資料庫。
transcripts_cache = {}

@router.post("/generate", response_model=GenerateResponse)
async def generate_presentation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    開始一個新的簡報生成任務。

    這是一個非同步端點。它會立即回傳一個 task_id，
    並將實際的處理工作（內容分析、圖片搜尋、簡報生成）
    交給一個背景任務 (BackgroundTasks) 處理。

    Args:
        request (GenerateRequest): 來自前端的請求，包含 'content' 和 'template'。
        background_tasks (BackgroundTasks): FastAPI 依賴注入，用於安排背景工作。

    Returns:
        GenerateResponse: 包含新任務 ID 和初始狀態 "processing" 的回應。
        
    呼叫的服務:
        - 本地: `content_processor.process_content` (在背景執行)
        - `content_processor` 接著將會呼叫：
            - Ollama 服務 (用於內容分析)
            - Pexels API (用於圖片搜尋)
            - Presenton 服務 (用於簡報生成)
    """
    
    task_id = str(uuid.uuid4())
    
    # 將耗時的任務交給背景處理
    background_tasks.add_task(
        content_processor.process_content,
        request.content,
        request.template.value,
        task_id
    )
    
    return GenerateResponse(
        task_id=task_id,
        status="processing",
        progress=0,
        message="開始處理內容..."
    )

@router.get("/progress/{task_id}", response_model=ProgressResponse)
async def get_progress(task_id: str):
    """
    查詢特定簡報生成任務的目前進度。

    前端在呼叫 /generate 後，會以輪詢 (polling) 方式
    (例如每秒一次) 呼叫此端點來更新 UI 上的進度條。

    Args:
        task_id (str): 從 /generate 取得的任務 ID。

    Returns:
        ProgressResponse: 包含目前進度百分比、狀態和訊息。
                          如果任務完成，還會包含 presentation_id。
                          
    呼叫的服務:
        - 本地: `content_processor.get_task_status`
        - (注意：此端點不會呼叫 Presenton 或 Ollama，
          它只讀取 content_processor 儲存在記憶體中的任務狀態)
    """
    
    status = content_processor.get_task_status(task_id)
    
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="任務不存在")
    
    return ProgressResponse(**status)

@router.get("/download/{presentation_id}/{format}")
async def download_presentation(presentation_id: str, format: str):
    """
    下載已生成的簡報檔案 (PPTX 或 PDF)。

    Args:
        presentation_id (str): 在 /progress 端點回報 "completed" 時取得的 ID。
        format (str): "pptx" 或 "pdf"。

    Returns:
        FileResponse: 一個檔案串流，觸發瀏覽器下載。
        
    呼叫的服務:
        - 遠端 Presenton API:
          `presenton.download_presentation(presentation_id, format)`
          (這會從 Presenton 服務下載檔案二進位內容)
    """
    
    if format not in ["pptx", "pdf"]:
        raise HTTPException(status_code=400, detail="不支援的格式")
    
    try:
        # 從 Presenton 服務下載檔案
        content = await presenton.download_presentation(presentation_id, format)
        
        # 暫存檔案以便回傳
        output_dir = settings.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{presentation_id}.{format}"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        return FileResponse(
            filepath,
            media_type="application/octet-stream",
            filename=f"簡報_{presentation_id}.{format}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下載失敗: {str(e)}")

@router.post("/transcript/generate", response_model=TranscriptResponse)
async def generate_transcript(request: TranscriptRequest):
    """
    為已生成的簡報產生一份演講稿。

    Args:
        request (TranscriptRequest): 包含 'presentation_id' 和 'style'。

    Returns:
        TranscriptResponse: 包含逐字稿和預估時間的完整資料。
        
    呼叫的服務:
        - 本地: `content_processor.tasks` (讀取簡報資料)
        - Ollama 服務: `zephyr.generate_transcript` (使用 LLM 生成演講稿)
        - (注意：此端點不會呼叫 Presenton 服務)
    """
    
    # 檢查 Zephyr (或指定的演講稿模型) 是否可用
    if not await zephyr.check_model_availability():
        raise HTTPException(
            status_code=503,
            detail=f"演講稿模型 {settings.ollama_model} 不可用。請執行: ollama pull {settings.ollama_model}"
        )
    
    # 從記憶體中尋找簡報資料
    presentation_data = None
    for task_id, task_data in content_processor.tasks.items():
        if task_data.get("presentation_id") == request.presentation_id:
            presentation_data = task_data.get("presentation")
            break
    
    if not presentation_data:
        raise HTTPException(
            status_code=404,
            detail="簡報資料不存在。請先生成簡報。"
        )
    
    try:
        # 呼叫 Zephyr (Ollama) 服務生成演講稿
        slides = presentation_data.get("slides", [])
        transcript_data = await zephyr.generate_transcript(
            slides=slides,
            style=request.style,
            language=request.language
        )
        
        # 快取演講稿
        transcripts_cache[request.presentation_id] = transcript_data
        
        return TranscriptResponse(
            presentation_id=request.presentation_id,
            **transcript_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成演講稿失敗: {str(e)}"
        )

@router.get("/transcript/{presentation_id}/download")
async def download_transcript(presentation_id: str):
    """
    下載演講稿為 .txt 檔案。

    Args:
        presentation_id (str): 簡報 ID。

    Returns:
        FileResponse: 包含演講稿的 .txt 檔案。
        
    呼叫的服務:
        - 本地: `transcripts_cache` (讀取記憶體快取)
        - (注意：此端點不呼叫任何遠端服務)
    """
    
    transcript_data = transcripts_cache.get(presentation_id)
    
    if not transcript_data:
        raise HTTPException(
            status_code=404,
            detail="演講稿不存在。請先生成演講稿。"
        )
    
    # ... (建立 .txt 檔案的邏輯) ...
    
    output_dir = settings.output_dir
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{presentation_id}_transcript.txt"
    filepath = os.path.join(output_dir, filename)
    
    header = f"""簡報演講稿
{'=' * 50}
投影片數量: {transcript_data.get('total_slides', 0)}
預估演講時間: {transcript_data.get('total_duration_minutes', 0)} 分鐘
{'=' * 50}\n\n"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(transcript_data.get("full_transcript", ""))
    
    return FileResponse(
        filepath,
        media_type="text/plain; charset=utf-8",
        filename=f"演講稿_{presentation_id}.txt"
    )

# ... (其他如 /health 的端點) ...
```

-----

## 步驟 3：前端 API 呼叫參考

以下是 `frontend/index.html` 中的 JavaScript 程式碼如何對應到我們剛剛記錄的後端 API 端點 (Goal 3)。

| 前端函式 (位於 `frontend/index.html`) | 呼叫的 API 端點 (位於 `backend/app/api/routes.py`) | 目的 |
| :--- | :--- | :--- |
| `generatePresentation()` | `POST /api/generate` | **開始生成：** 提交內容和模板，獲取 `task_id`。 |
| `pollProgress(taskId)` | `GET /api/progress/{task_id}` | **輪詢進度：** 每秒檢查一次任務狀態，以更新進度條。 |
| `downloadFile(format)` | `GET /api/download/{presentation_id}/{format}` | **下載簡報：** 獲取 `pptx` 或 `pdf` 檔案。 |
| `generateTranscript()` | `POST /api/transcript/generate` | **生成演講稿：** 提交 `presentation_id` 和風格，獲取演講稿 JSON。 |
| `downloadTranscript()` | `GET /api/transcript/{presentation_id}/download` | **下載演講稿：** 獲取演講稿的 `.txt` 檔案。 |

這種設計非常出色：

1.  **前端保持簡潔：** 前端只需要知道 5 個 API 端點，所有複雜的協調（Ollama, Pexels, Presenton）都由後端處理。
2.  **非同步處理：** `generate` 函式立即回傳，`pollProgress` 負責更新，提供了極佳的使用者體驗，避免了瀏覽器請求超時。