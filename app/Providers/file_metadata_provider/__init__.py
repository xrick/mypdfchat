"""
File Metadata Provider Module

SQLite-based file tracking and metadata storage.
"""

from app.Providers.file_metadata_provider.client import (
    FileMetadataProvider,
    get_file_metadata_provider
)

__all__ = ["FileMetadataProvider", "get_file_metadata_provider"]
