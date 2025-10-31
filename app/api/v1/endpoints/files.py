# app/api/v1/endpoints/files.py
"""
File Management API Endpoints

Handles file listing and deletion operations with user authorization.

GET /api/v1/files - List files owned by user
DELETE /api/v1/files/{file_id} - Delete file (owner only)
"""

import logging
from fastapi import APIRouter, Header, HTTPException, Query, Depends
from typing import List, Dict, Any
from pathlib import Path

# Application imports
from app.Providers.file_metadata_provider.client import (
    FileMetadataProvider,
    get_file_metadata_provider
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["file-management"])


@router.get("", summary="List user files", description="Get all files owned by the authenticated user")
async def list_user_files(
    user_id: str = Header(..., alias="X-User-ID", description="User UUID (required)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip (pagination)"),
    file_metadata_provider: FileMetadataProvider = Depends(get_file_metadata_provider)
):
    """
    List all files owned by the authenticated user

    Args:
        user_id: User identifier from X-User-ID header (UUID v4)
        limit: Maximum files to return (1-100, default: 50)
        offset: Pagination offset (default: 0)
        file_metadata_provider: File metadata provider (dependency injection)

    Returns:
        Dict with user_id, files list, and count

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/v1/files?limit=10" \\
          -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000"
        ```

    Response:
        ```json
        {
            "user_id": "550e8400-...",
            "files": [
                {
                    "file_id": "file_1698765432_a1b2c3d4_e5f6g7h8",
                    "filename": "document.pdf",
                    "file_size": 1048576,
                    "upload_time": "2025-10-31T12:34:56",
                    "chunk_count": 25,
                    "embedding_status": "completed"
                }
            ],
            "count": 1,
            "limit": 10,
            "offset": 0
        }
        ```
    """
    try:
        # Validate user_id format (UUID v4)
        import re
        UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(UUID_PATTERN, user_id, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid user_id format. Must be UUID v4.",
                    "details": {"user_id": user_id}
                }
            )

        # Get files for user
        files = await file_metadata_provider.list_files_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return {
            "user_id": user_id,
            "files": files,
            "count": len(files),
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": f"Failed to retrieve files: {str(e)}",
                "details": {}
            }
        )


@router.delete("/{file_id}", summary="Delete file", description="Delete file owned by user")
async def delete_file(
    file_id: str,
    user_id: str = Header(..., alias="X-User-ID", description="User UUID (required)"),
    file_metadata_provider: FileMetadataProvider = Depends(get_file_metadata_provider)
):
    """
    Delete file (only owner can delete)

    Args:
        file_id: File identifier to delete
        user_id: User identifier from X-User-ID header (UUID v4)
        file_metadata_provider: File metadata provider (dependency injection)

    Returns:
        Success message with deleted file_id

    Raises:
        HTTPException:
            - 400: Invalid user_id format
            - 403: User doesn't own this file (authorization failure)
            - 404: File not found
            - 500: Database or file system error

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/v1/files/file_1698765432_a1b2c3d4_e5f6g7h8" \\
          -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000"
        ```

    Response:
        ```json
        {
            "message": "File deleted successfully",
            "file_id": "file_1698765432_a1b2c3d4_e5f6g7h8"
        }
        ```
    """
    try:
        # Validate user_id format (UUID v4)
        import re
        UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(UUID_PATTERN, user_id, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid user_id format. Must be UUID v4.",
                    "details": {"user_id": user_id}
                }
            )

        # Get file metadata to check ownership
        file_data = await file_metadata_provider.get_file(file_id)

        if not file_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"File not found: {file_id}",
                    "details": {"file_id": file_id}
                }
            )

        # Authorization check: User must own the file
        if file_data.get("user_id") != user_id:
            logger.warning(
                f"Authorization failed: User {user_id} attempted to delete file {file_id} "
                f"owned by {file_data.get('user_id')}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": "You can only delete your own files",
                    "details": {"file_id": file_id}
                }
            )

        # Delete from database
        await file_metadata_provider.delete_file(file_id)

        # Delete physical file from disk (if exists)
        try:
            file_path = Path(settings.PDF_UPLOAD_DIR) / f"{file_id}.pdf"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted physical file: {file_path}")
        except Exception as e:
            # Log but don't fail if physical file deletion fails
            logger.warning(f"Failed to delete physical file for {file_id}: {str(e)}")

        logger.info(f"File deleted successfully: {file_id} by user {user_id}")

        return {
            "message": "File deleted successfully",
            "file_id": file_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DeletionError",
                "message": f"Failed to delete file: {str(e)}",
                "details": {"file_id": file_id}
            }
        )
