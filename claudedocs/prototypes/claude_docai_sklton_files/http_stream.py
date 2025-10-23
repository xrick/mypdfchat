"""
Presentation Layer - FastAPI HTTP Streaming with SSE
"""
import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.core_logic import CoreLogicService
from app.infra.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# Service will be injected
core_service: Optional[CoreLogicService] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    session_id: str
    response: str
    sources: list = []


def format_sse(data: dict) -> str:
    """
    Format data as Server-Sent Events message
    
    Args:
        data: Dictionary to send as SSE
        
    Returns:
        Formatted SSE string
    """
    return f"data: {json.dumps(data)}\n\n"


async def chat_stream_generator(query: str, session_id: str):
    """
    Generator for streaming chat responses
    
    Args:
        query: User query
        session_id: Session identifier
        
    Yields:
        SSE formatted messages
    """
    try:
        if not core_service:
            raise HTTPException(status_code=500, detail="Service not initialized")
        
        async for update in core_service.chat_stream_progressive(
            query=query,
            session_id=session_id
        ):
            yield format_sse(update)
            
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_msg = {
            "type": "error",
            "message": str(e)
        }
        yield format_sse(error_msg)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses with OPMP progressive rendering
    
    Returns Server-Sent Events stream with:
    - Progress updates for each phase
    - Markdown tokens as they're generated
    - Final complete response with metadata
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    return StreamingResponse(
        chat_stream_generator(request.query, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LLM RAG Application"}
