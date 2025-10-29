"""
Pydantic Schemas for API Request/Response Models

All data validation and serialization models for the DocAI RAG application.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


# =============================================================================
# Upload Endpoint Schemas
# =============================================================================

class UploadResponse(BaseModel):
    """Response model for file upload"""
    file_id: str = Field(..., description="Unique identifier for uploaded file")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    chunk_count: int = Field(..., description="Number of text chunks generated")
    embedding_status: str = Field(..., description="Status: 'pending', 'completed', 'failed'")
    message: str = Field(default="File uploaded and indexed successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123def456",
                "filename": "document.pdf",
                "file_size": 1024000,
                "chunk_count": 150,
                "embedding_status": "completed",
                "message": "File uploaded and indexed successfully"
            }
        }


# =============================================================================
# Chat Endpoint Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to search")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages (format: [{'role': 'user'|'assistant', 'content': '...'}])"
    )
    enable_query_enhancement: Optional[bool] = Field(
        default=True,
        description="Enable Strategy 2 Query Expansion"
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve"
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one file_id is required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the main topic of this document?",
                "file_ids": ["file_abc123"],
                "session_id": "session_xyz789",
                "chat_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"}
                ],
                "enable_query_enhancement": True,
                "top_k": 5,
                "temperature": 0.7
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint (non-streaming)"""
    answer: str = Field(..., description="Generated answer")
    session_id: str = Field(..., description="Session ID for this conversation")
    query_enhancement: Optional[Dict[str, Any]] = Field(
        None,
        description="Query expansion details (if enabled)"
    )
    retrieved_chunks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved context chunks with metadata"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (model, tokens, timing)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Based on the document, the main topic is...",
                "session_id": "session_xyz789",
                "query_enhancement": {
                    "original_query": "What is the main topic?",
                    "expanded_questions": ["Q1", "Q2", "Q3"],
                    "intent": "information_seeking"
                },
                "retrieved_chunks": [
                    {
                        "content": "Chunk text...",
                        "file_id": "file_abc123",
                        "chunk_index": 5,
                        "score": 0.85
                    }
                ],
                "metadata": {
                    "model": "gpt-oss:20b",
                    "total_tokens": 500,
                    "response_time_ms": 1200
                }
            }
        }


# =============================================================================
# History Endpoint Schemas
# =============================================================================

class MessageSchema(BaseModel):
    """Individual message in conversation history"""
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Message-specific metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What is RAG?",
                "timestamp": "2025-10-29T12:00:00Z",
                "metadata": {
                    "original_query": "What is RAG?",
                    "expanded_questions": ["Q1", "Q2"]
                }
            }
        }


class SessionResponse(BaseModel):
    """Response model for session history retrieval"""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    file_ids: List[str] = Field(default_factory=list, description="Files associated with session")
    messages: List[MessageSchema] = Field(default_factory=list, description="Conversation messages")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Session-level metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_xyz789",
                "user_id": "user_123",
                "file_ids": ["file_abc", "file_def"],
                "messages": [
                    {
                        "role": "user",
                        "content": "What is RAG?",
                        "timestamp": "2025-10-29T12:00:00Z",
                        "metadata": {}
                    }
                ],
                "created_at": "2025-10-29T12:00:00Z",
                "updated_at": "2025-10-29T12:30:00Z",
                "metadata": {
                    "total_messages": 10,
                    "total_tokens": 5000
                }
            }
        }


class SessionListResponse(BaseModel):
    """Response model for listing user sessions"""
    sessions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of session summaries"
    )
    total_count: int = Field(..., description="Total number of sessions")

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "session_id": "session_1",
                        "created_at": "2025-10-29T10:00:00Z",
                        "message_count": 5,
                        "file_ids": ["file_abc"]
                    },
                    {
                        "session_id": "session_2",
                        "created_at": "2025-10-29T11:00:00Z",
                        "message_count": 3,
                        "file_ids": ["file_def"]
                    }
                ],
                "total_count": 2
            }
        }


# =============================================================================
# Export Endpoint Schemas
# =============================================================================

class ExportFormat(str):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"


class ExportRequest(BaseModel):
    """Request model for export endpoint"""
    session_id: str = Field(..., description="Session to export")
    format: ExportFormat = Field(default=ExportFormat.JSON, description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata in export")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_xyz789",
                "format": "json",
                "include_metadata": True
            }
        }


# =============================================================================
# Query Enhancement Schemas (Strategy 2)
# =============================================================================

class QueryExpansion(BaseModel):
    """Query expansion result from Strategy 2"""
    original_query: str = Field(..., description="Original user query")
    intent: str = Field(..., description="Identified query intent")
    expanded_questions: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Expanded sub-questions"
    )
    reasoning: Optional[str] = Field(None, description="Reasoning for expansion")

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "What is RAG?",
                "intent": "definition_seeking",
                "expanded_questions": [
                    "What does RAG stand for?",
                    "How does RAG work technically?",
                    "What are the benefits of using RAG?"
                ],
                "reasoning": "User seeks comprehensive understanding of RAG concept"
            }
        }


# =============================================================================
# Error Response Schemas
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid file_id format",
                "details": {
                    "field": "file_ids",
                    "provided": "invalid_id"
                },
                "timestamp": "2025-10-29T12:00:00Z"
            }
        }


# =============================================================================
# Health Check Schemas
# =============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status: 'healthy', 'degraded', 'unhealthy'")
    version: str = Field(..., description="Application version")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services (Milvus, MongoDB, Redis)"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "milvus": "connected",
                    "mongodb": "connected",
                    "redis": "connected",
                    "llm_provider": "connected"
                },
                "timestamp": "2025-10-29T12:00:00Z"
            }
        }
