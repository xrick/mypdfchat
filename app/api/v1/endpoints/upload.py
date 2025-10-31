# app/api/v1/endpoints/upload.py
"""
Upload API Endpoint

Handles PDF file uploads with text extraction, hierarchical chunking, and vectorization.

POST /api/v1/upload - Upload single PDF file for processing
"""

import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Header
from pathlib import Path
import shutil
from typing import Optional

# Application imports
from app.models.schemas import UploadResponse, ErrorResponse
from app.Services.input_data_handle_service import (
    InputDataHandleService,
    get_input_data_service
)
from app.Providers.file_metadata_provider.client import (
    FileMetadataProvider,
    get_file_metadata_provider
)
from app.Providers.embedding_provider.client import (
    get_embedding_provider
)
from app.Services.retrieval_service import (
    RetrievalService,
    get_retrieval_service
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


# =============================================================================
# Helper Functions
# =============================================================================

def save_uploaded_file(file_content: bytes, filename: str, file_id: str) -> Path:
    """
    Save uploaded file content to disk

    Args:
        file_content: Binary file content
        filename: Original filename (for extension extraction)
        file_id: Generated file identifier

    Returns:
        Path to saved file

    Example:
        >>> file_path = save_uploaded_file(content, "doc.pdf", "file_abc123")
    """
    # Ensure upload directory exists
    upload_dir = Path(settings.PDF_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save with file_id as filename
    file_extension = Path(filename).suffix
    file_path = upload_dir / f"{file_id}{file_extension}"

    # Write binary content directly
    with file_path.open("wb") as buffer:
        buffer.write(file_content)

    logger.info(f"Saved uploaded file: {file_path} ({len(file_content)} bytes)")
    return file_path


async def process_and_embed_file(
    file_content: bytes,
    filename: str,
    user_id: str,
    input_service: InputDataHandleService,
    retrieval_service: RetrievalService,
    file_metadata_provider: FileMetadataProvider,
    embedding_provider
) -> dict:
    """
    Process file and generate embeddings (Multi-User Support)

    Workflow:
    1. Extract text from PDF
    2. Chunk text using hierarchical strategy
    3. Generate embeddings for chunks
    4. Store in vector database
    5. Update file metadata with user ownership

    Args:
        file_content: Binary file content
        filename: Original filename
        user_id: User identifier (UUID format)
        input_service: Input data handle service
        retrieval_service: Retrieval service for embedding
        file_metadata_provider: File metadata provider
        embedding_provider: Embedding provider

    Returns:
        Processing result dict with user_id

    Example:
        >>> result = await process_and_embed_file(
        ...     content, "doc.pdf", "550e8400-...", ...
        ... )
    """
    try:
        # Step 1: Process file (extract + chunk) with unique file_id generation
        process_result = await input_service.process_file(
            file_content,
            filename,
            file_metadata_provider  # Pass provider for collision detection
        )

        file_id = process_result["file_id"]
        chunks = process_result["chunks"]
        chunk_count = process_result["chunk_count"]

        logger.info(
            f"File processed: {file_id}, {chunk_count} chunks "
            f"(strategy: {process_result['chunking_strategy']})"
        )

        # Step 2: Store file metadata in SQLite (with user ownership)
        await file_metadata_provider.add_file(
            file_id=file_id,
            filename=filename,
            file_type="pdf",
            file_size=process_result["file_size"],
            user_id=user_id,  # NEW: Associate file with user
            chunk_count=chunk_count,
            milvus_partition=f"file_{file_id}",
            metadata={
                "chunking_strategy": process_result["chunking_strategy"],
                "chunk_sizes": settings.HIERARCHICAL_CHUNK_SIZES if settings.CHUNKING_STRATEGY == "hierarchical" else None
            }
        )

        # Step 3: Extract chunk texts and metadata for embedding
        chunk_texts = [chunk["content"] for chunk in chunks]
        chunk_metadata = [chunk["metadata"] for chunk in chunks]

        # Step 4: Add chunks to vector store (with embeddings)
        store_id = await retrieval_service.add_document_chunks(
            file_id=file_id,
            chunks=chunk_texts,
            metadata=chunk_metadata
        )

        logger.info(f"Embeddings generated and stored: {store_id}")

        # Step 5: Update embedding status
        await file_metadata_provider.update_embedding_status(file_id, "completed")

        return {
            "file_id": file_id,
            "filename": filename,
            "file_size": process_result["file_size"],
            "chunk_count": chunk_count,
            "embedding_status": "completed",
            "chunking_strategy": process_result["chunking_strategy"]
        }

    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        # Update status to failed if file_id exists
        if "file_id" in locals():
            try:
                await file_metadata_provider.update_embedding_status(file_id, "failed")
            except:
                pass
        raise


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or validation error"},
        500: {"model": ErrorResponse, "description": "Server error during processing"}
    },
    summary="Upload PDF file for RAG indexing",
    description="""
    Upload a single PDF file for processing with hierarchical chunking and embedding generation.

    **Workflow**:
    1. Validate PDF file (type, size, content)
    2. Extract text using PyPDF2
    3. Chunk text using configured strategy (hierarchical or recursive)
    4. Generate embeddings using HuggingFace model
    5. Store embeddings in Milvus vector database
    6. Save file metadata to SQLite

    **Chunking Strategy**:
    - **Hierarchical Indexing** (default): Multi-level chunks with parent-child relationships
      - Parent chunks (2000 chars): Broad context
      - Child chunks (1000 chars): Retrieval targets
      - Grandchild chunks (500 chars): Precision matching
    - **Recursive** (fallback): Standard character-based splitting

    **Constraints**:
    - Max file size: 50MB
    - Supported format: PDF only
    - Processing time: ~1-5 seconds per MB
    """
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    user_id: str = Header(..., alias="X-User-ID", description="User UUID (required)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    input_service: InputDataHandleService = Depends(get_input_data_service),
    file_metadata_provider: FileMetadataProvider = Depends(get_file_metadata_provider),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    embedding_provider = Depends(get_embedding_provider)
):
    """
    Upload PDF file for processing and indexing (Multi-User Support)

    Args:
        file: Uploaded PDF file
        user_id: User identifier (UUID v4 format, required via X-User-ID header)
        background_tasks: FastAPI background tasks for async processing
        input_service: Input data handle service (dependency injection)
        file_metadata_provider: File metadata provider (dependency injection)
        retrieval_service: Retrieval service (dependency injection)
        embedding_provider: Embedding provider (dependency injection)

    Returns:
        UploadResponse with file_id, filename, chunk_count, status

    Raises:
        HTTPException: 400 for validation errors, 500 for processing errors

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/upload" \\
          -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \\
          -F "file=@document.pdf"
        ```
    """
    # Validate user_id format (UUID v4)
    import re
    UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    if not re.match(UUID_PATTERN, user_id, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid user_id format. Must be UUID v4.",
                "details": {"user_id": user_id, "expected_format": "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"}
            }
        )
    try:
        # Validate file extension
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Only PDF files are allowed",
                    "details": {"filename": file.filename}
                }
            )

        # Read file content
        file_content = await file.read()

        # Validate file (uses InputDataHandleService validation)
        is_valid, error_msg = input_service.validate_file(file_content, file.filename)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": error_msg,
                    "details": {"filename": file.filename}
                }
            )

        # Process file and generate embeddings (with user ownership)
        result = await process_and_embed_file(
            file_content=file_content,
            filename=file.filename,
            user_id=user_id,  # NEW: Pass user_id for ownership tracking
            input_service=input_service,
            retrieval_service=retrieval_service,
            file_metadata_provider=file_metadata_provider,
            embedding_provider=embedding_provider
        )

        # Save file to disk using the already-read content
        file_path = save_uploaded_file(file_content, file.filename, result["file_id"])

        logger.info(
            f"File upload completed: {result['file_id']} "
            f"({result['chunk_count']} chunks, {result['chunking_strategy']} strategy)"
        )

        # Return response
        return UploadResponse(
            file_id=result["file_id"],
            filename=result["filename"],
            file_size=result["file_size"],
            chunk_count=result["chunk_count"],
            embedding_status=result["embedding_status"],
            message=f"File uploaded and indexed successfully using {result['chunking_strategy']} chunking"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ProcessingError",
                "message": f"Failed to process file: {str(e)}",
                "details": {}
            }
        )
