# app/api/v1/router.py
"""
API v1 Router

Aggregates all v1 API endpoints.
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import upload, chat

# Create main v1 router
router = APIRouter(prefix="/v1")

# Register endpoint routers
router.include_router(upload.router, prefix="", tags=["upload"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Future endpoints can be added here:
# from app.api.v1.endpoints import history
# router.include_router(history.router, prefix="", tags=["history"])
