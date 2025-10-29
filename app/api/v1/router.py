"""
API v1 Router

Aggregates all v1 API endpoints.
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import upload

# Create main v1 router
router = APIRouter(prefix="/v1")

# Register endpoint routers
router.include_router(upload.router, prefix="", tags=["upload"])

# Future endpoints can be added here:
# from app.api.v1.endpoints import chat, history
# router.include_router(chat.router, prefix="", tags=["chat"])
# router.include_router(history.router, prefix="", tags=["history"])
