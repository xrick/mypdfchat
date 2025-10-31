"""
SQLite File Metadata Provider

Lightweight relational database for file tracking, chunk metadata, and indexing status.
Implements async operations using aiosqlite.
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import aiosqlite

logger = logging.getLogger(__name__)


class FileMetadataProvider:
    """
    SQLite File Metadata Provider

    Tables:
    1. file_metadata: File-level information
       - file_id (PK), filename, file_type, file_size
       - upload_time, user_id, chunk_count
       - embedding_status, milvus_partition, metadata_json

    2. chunks_metadata (optional): Chunk-level tracking
       - chunk_id (PK), file_id (FK), chunk_index
       - chunk_text, milvus_id
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize File Metadata Provider

        Args:
            db_path: Path to SQLite database file (default from settings)
        """
        from app.core.config import settings

        self.db_path = Path(db_path or settings.SQLITE_DB_PATH)
        self._connection: Optional[aiosqlite.Connection] = None

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"File Metadata Provider initialized: {self.db_path}")

    async def _get_connection(self) -> aiosqlite.Connection:
        """
        Get database connection (singleton, reuses same connection)

        Returns:
            Async SQLite connection
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(str(self.db_path))
            self._connection.row_factory = aiosqlite.Row  # Enable dict-like access
            logger.debug("Created new database connection")

        return self._connection

    async def initialize_database(self):
        """
        Create tables if they don't exist

        Call this once during application startup
        """
        conn = await self._get_connection()

        # Create file_metadata table
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    chunk_count INTEGER,
                    embedding_status TEXT,
                    milvus_partition TEXT,
                    metadata_json TEXT
                )
        """)

        # Create chunks_metadata table (optional, for detailed tracking)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks_metadata (
                chunk_id TEXT PRIMARY KEY,
                file_id TEXT,
                chunk_index INTEGER,
                chunk_text TEXT,
                milvus_id INTEGER,
                FOREIGN KEY (file_id) REFERENCES file_metadata(file_id)
            )
        """)

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_user
            ON file_metadata(user_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_upload_time
            ON file_metadata(upload_time)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_file_id
            ON chunks_metadata(file_id)
        """)

        await conn.commit()

        logger.info("Database tables initialized")

    # =========================================================================
    # File Metadata Operations
    # =========================================================================

    async def add_file(
        self,
        file_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        user_id: Optional[str] = None,
        chunk_count: Optional[int] = None,
        milvus_partition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add file metadata record

        Args:
            file_id: Unique file identifier
            filename: Original filename
            file_type: File extension (pdf, docx, txt, md)
            file_size: File size in bytes
            user_id: Optional user identifier
            chunk_count: Number of chunks generated
            milvus_partition: Partition name in Milvus
            metadata: Additional metadata as dict

        Example:
            >>> await provider.add_file(
            ...     file_id="file_abc123",
            ...     filename="document.pdf",
            ...     file_type="pdf",
            ...     file_size=1024000,
            ...     chunk_count=150
            ... )
        """
        conn = await self._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None

            await conn.execute("""
                INSERT INTO file_metadata (
                    file_id, filename, file_type, file_size,
                    upload_time, user_id, chunk_count,
                    embedding_status, milvus_partition, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, filename, file_type, file_size,
                datetime.now(timezone.utc).isoformat(),
                user_id, chunk_count,
                'pending', milvus_partition, metadata_json
            ))

            await conn.commit()
            logger.info(f"Added file metadata: {file_id}")

        except Exception as e:
                logger.error(f"Failed to add file metadata: {str(e)}")
                raise

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file metadata

        Args:
            file_id: File identifier

        Returns:
            File metadata dict or None if not found

        Example:
            >>> file = await provider.get_file("file_abc123")
            >>> if file:
            ...     print(f"Filename: {file['filename']}")
        """
        conn = await self._get_connection()
        try:
            async with conn.execute(
                "SELECT * FROM file_metadata WHERE file_id = ?",
                (file_id,)
            ) as cursor:
                row = await cursor.fetchone()

                if row:
                    file_data = dict(row)

                    # Parse metadata_json
                    if file_data.get('metadata_json'):
                        file_data['metadata'] = json.loads(file_data['metadata_json'])
                        del file_data['metadata_json']
                    else:
                        file_data['metadata'] = {}

                    return file_data

                return None

        except Exception as e:
                logger.error(f"Failed to get file metadata: {str(e)}")
                return None

    async def update_embedding_status(
        self,
        file_id: str,
        status: str
    ):
        """
        Update file embedding status

        Args:
            file_id: File identifier
            status: Status ('pending', 'completed', 'failed')

        Example:
            >>> await provider.update_embedding_status("file_abc", "completed")
        """
        conn = await self._get_connection()
        try:
            await conn.execute("""
                UPDATE file_metadata
                SET embedding_status = ?
                WHERE file_id = ?
            """, (status, file_id))

            await conn.commit()
            logger.debug(f"Updated embedding status for {file_id}: {status}")

        except Exception as e:
                logger.error(f"Failed to update embedding status: {str(e)}")
                raise

    async def list_files(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List files with optional user filter

        Args:
            user_id: Optional user identifier filter
            limit: Max number of files to return
            offset: Number of files to skip (pagination)

        Returns:
            List of file metadata dicts

        Example:
            >>> files = await provider.list_files(user_id="user_123", limit=10)
        """
        conn = await self._get_connection()
        try:
            if user_id:
                query = """
                    SELECT * FROM file_metadata
                    WHERE user_id = ?
                    ORDER BY upload_time DESC
                    LIMIT ? OFFSET ?
                """
                params = (user_id, limit, offset)
            else:
                query = """
                    SELECT * FROM file_metadata
                    ORDER BY upload_time DESC
                    LIMIT ? OFFSET ?
                """
                params = (limit, offset)

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()

                files = []
                for row in rows:
                    file_data = dict(row)

                    # Parse metadata_json
                    if file_data.get('metadata_json'):
                        file_data['metadata'] = json.loads(file_data['metadata_json'])
                        del file_data['metadata_json']
                    else:
                        file_data['metadata'] = {}

                    files.append(file_data)

                return files

        except Exception as e:
                logger.error(f"Failed to list files: {str(e)}")
                return []

    async def delete_file(self, file_id: str):
        """
        Delete file metadata and associated chunks

        Args:
            file_id: File identifier

        Example:
            >>> await provider.delete_file("file_abc123")
        """
        conn = await self._get_connection()
        try:
            # Delete chunks first (foreign key constraint)
            await conn.execute(
                "DELETE FROM chunks_metadata WHERE file_id = ?",
                (file_id,)
            )

            # Delete file metadata
            await conn.execute(
                "DELETE FROM file_metadata WHERE file_id = ?",
                (file_id,)
            )

            await conn.commit()
            logger.info(f"Deleted file metadata: {file_id}")

        except Exception as e:
                logger.error(f"Failed to delete file metadata: {str(e)}")
                raise

    # =========================================================================
    # Chunk Metadata Operations (Optional Fine-grained Tracking)
    # =========================================================================

    async def add_chunks(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]]
    ):
        """
        Add chunk metadata records

        Args:
            file_id: File identifier
            chunks: List of chunk dicts with keys: chunk_id, chunk_index, chunk_text, milvus_id

        Example:
            >>> chunks = [
            ...     {"chunk_id": "chunk_0", "chunk_index": 0, "chunk_text": "...", "milvus_id": 1},
            ...     {"chunk_id": "chunk_1", "chunk_index": 1, "chunk_text": "...", "milvus_id": 2}
            ... ]
            >>> await provider.add_chunks("file_abc", chunks)
        """
        conn = await self._get_connection()
        try:
            for chunk in chunks:
                await conn.execute("""
                    INSERT INTO chunks_metadata (
                        chunk_id, file_id, chunk_index, chunk_text, milvus_id
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    chunk['chunk_id'],
                    file_id,
                    chunk['chunk_index'],
                    chunk.get('chunk_text', ''),
                    chunk.get('milvus_id')
                ))

            await conn.commit()
            logger.debug(f"Added {len(chunks)} chunk records for file {file_id}")

        except Exception as e:
                logger.error(f"Failed to add chunk metadata: {str(e)}")
                raise

    async def get_file_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a file

        Args:
            file_id: File identifier

        Returns:
            List of chunk metadata dicts
        """
        conn = await self._get_connection()
        try:
            async with conn.execute(
                "SELECT * FROM chunks_metadata WHERE file_id = ? ORDER BY chunk_index",
                (file_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
                logger.error(f"Failed to get file chunks: {str(e)}")
                return []

    # =========================================================================
    # Statistics and Utilities
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Dict with stats (total_files, total_chunks, total_size)

        Example:
            >>> stats = await provider.get_stats()
            >>> print(f"Total files: {stats['total_files']}")
        """
        conn = await self._get_connection()
        try:
            # Total files
            async with conn.execute("SELECT COUNT(*) FROM file_metadata") as cursor:
                total_files = (await cursor.fetchone())[0]

            # Total chunks
            async with conn.execute("SELECT COUNT(*) FROM chunks_metadata") as cursor:
                total_chunks = (await cursor.fetchone())[0]

            # Total file size
            async with conn.execute("SELECT SUM(file_size) FROM file_metadata") as cursor:
                total_size = (await cursor.fetchone())[0] or 0

            stats = {
                "total_files": total_files,
                "total_chunks": total_chunks,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }

            return stats

        except Exception as e:
                logger.error(f"Failed to get database stats: {str(e)}")
                return {}


# Singleton instance for dependency injection
_file_metadata_provider_instance: Optional[FileMetadataProvider] = None
_database_initialized: bool = False


async def get_file_metadata_provider() -> FileMetadataProvider:
    """
    FastAPI dependency for File Metadata Provider (Singleton)

    Usage in endpoints:
        @router.post("/upload")
        async def upload(
            file_metadata: FileMetadataProvider = Depends(get_file_metadata_provider)
        ):
            ...
    """
    global _file_metadata_provider_instance, _database_initialized

    if _file_metadata_provider_instance is None:
        _file_metadata_provider_instance = FileMetadataProvider()

    # Initialize database only once (thread-safe initialization)
    if not _database_initialized:
        await _file_metadata_provider_instance.initialize_database()
        _database_initialized = True

    return _file_metadata_provider_instance
