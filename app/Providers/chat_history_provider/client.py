"""
MongoDB Chat History Provider

Persistent conversation storage with session management and message retrieval.
Implements async operations using Motor (async MongoDB driver).
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class ChatHistoryProvider:
    """
    MongoDB Chat History Provider

    Schema (collection: chat_sessions):
    {
        "_id": ObjectId,
        "session_id": str (unique),
        "user_id": str (optional),
        "file_ids": List[str],
        "created_at": datetime,
        "updated_at": datetime,
        "messages": [
            {
                "role": "user" | "assistant" | "system",
                "content": str,
                "timestamp": datetime,
                "metadata": dict (optional)
            }
        ],
        "metadata": dict (optional, session-level stats)
    }
    """

    def __init__(
        self,
        mongodb_uri: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialize Chat History Provider

        Args:
            mongodb_uri: MongoDB connection URI (default from settings)
            database_name: Database name (default from settings)
            collection_name: Collection name (default from settings)
        """
        from app.core.config import settings

        self.mongodb_uri = mongodb_uri or settings.MONGODB_URI
        self.database_name = database_name or settings.MONGODB_DATABASE
        self.collection_name = collection_name or settings.MONGODB_CHAT_COLLECTION

        # MongoDB client (initialized lazily)
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._collection: Optional[AsyncIOMotorCollection] = None

        logger.info(
            f"Chat History Provider initialized: "
            f"db={self.database_name}, collection={self.collection_name}"
        )

    async def _get_collection(self) -> AsyncIOMotorCollection:
        """
        Lazy initialization of MongoDB connection

        Returns:
            MongoDB collection instance
        """
        if self._collection is None:
            self._client = AsyncIOMotorClient(self.mongodb_uri)
            self._db = self._client[self.database_name]
            self._collection = self._db[self.collection_name]

            # Create index on session_id for faster lookups
            await self._collection.create_index("session_id", unique=True)
            await self._collection.create_index("user_id")
            await self._collection.create_index("created_at")

            logger.info("MongoDB chat_sessions collection initialized")

        return self._collection

    # =========================================================================
    # Session Management
    # =========================================================================

    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create new chat session

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            file_ids: Files associated with this session
            metadata: Additional session metadata

        Returns:
            Created session document

        Example:
            >>> session = await provider.create_session(
            ...     session_id="session_xyz",
            ...     user_id="user_123",
            ...     file_ids=["file_abc"]
            ... )
        """
        collection = await self._get_collection()

        now = datetime.now(timezone.utc)

        session_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "file_ids": file_ids or [],
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "metadata": metadata or {}
        }

        try:
            await collection.insert_one(session_doc)
            logger.info(f"Created session: {session_id}")
            return session_doc

        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session document or None if not found

        Example:
            >>> session = await provider.get_session("session_xyz")
            >>> if session:
            ...     messages = session['messages']
        """
        collection = await self._get_collection()

        try:
            session = await collection.find_one({"session_id": session_id})

            if session:
                # Remove MongoDB's _id from response
                session.pop('_id', None)
                logger.debug(f"Retrieved session: {session_id}")
                return session

            logger.debug(f"Session not found: {session_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        collection = await self._get_collection()

        try:
            count = await collection.count_documents({"session_id": session_id})
            return count > 0

        except Exception as e:
            logger.error(f"Failed to check session existence: {str(e)}")
            return False

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add message to session

        Args:
            session_id: Session identifier
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Optional message-specific metadata

        Example:
            >>> await provider.add_message(
            ...     session_id="session_xyz",
            ...     role="user",
            ...     content="What is RAG?",
            ...     metadata={"original_query": "What is RAG?"}
            ... )
        """
        collection = await self._get_collection()

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }

        try:
            result = await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                    "$inc": {"metadata.total_messages": 1}
                }
            )

            if result.modified_count > 0:
                logger.debug(f"Added {role} message to session: {session_id}")
            else:
                logger.warning(f"Session not found when adding message: {session_id}")

        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {str(e)}")
            raise

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages from session

        Args:
            session_id: Session identifier
            limit: Optional limit on number of recent messages

        Returns:
            List of message dicts

        Example:
            >>> messages = await provider.get_messages("session_xyz", limit=10)
            >>> for msg in messages:
            ...     print(f"{msg['role']}: {msg['content']}")
        """
        session = await self.get_session(session_id)

        if not session:
            return []

        messages = session.get('messages', [])

        if limit:
            messages = messages[-limit:]

        return messages

    async def get_chat_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get chat history in LangChain format

        Args:
            session_id: Session identifier
            limit: Optional limit on number of recent messages

        Returns:
            List of dicts with 'role' and 'content' keys

        Example:
            >>> history = await provider.get_chat_history("session_xyz")
            >>> # Returns: [{"role": "user", "content": "..."}, ...]
        """
        messages = await self.get_messages(session_id, limit)

        # Convert to simple format (drop timestamp and metadata)
        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

        return chat_history

    # =========================================================================
    # Session Queries
    # =========================================================================

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List sessions for a user

        Args:
            user_id: User identifier
            limit: Max number of sessions to return
            skip: Number of sessions to skip (pagination)

        Returns:
            List of session documents

        Example:
            >>> sessions = await provider.list_user_sessions("user_123", limit=10)
        """
        collection = await self._get_collection()

        try:
            cursor = collection.find(
                {"user_id": user_id}
            ).sort("updated_at", -1).skip(skip).limit(limit)

            sessions = await cursor.to_list(length=limit)

            # Remove _id from each session
            for session in sessions:
                session.pop('_id', None)

            logger.debug(f"Retrieved {len(sessions)} sessions for user: {user_id}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {str(e)}")
            return []

    async def update_session_metadata(
        self,
        session_id: str,
        metadata_updates: Dict[str, Any]
    ):
        """
        Update session-level metadata

        Args:
            session_id: Session identifier
            metadata_updates: Metadata fields to update

        Example:
            >>> await provider.update_session_metadata(
            ...     session_id="session_xyz",
            ...     metadata_updates={"total_tokens": 5000, "language": "zh"}
            ... )
        """
        collection = await self._get_collection()

        try:
            # Prepare updates with proper nesting
            updates = {
                f"metadata.{key}": value
                for key, value in metadata_updates.items()
            }
            updates["updated_at"] = datetime.now(timezone.utc)

            await collection.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )

            logger.debug(f"Updated metadata for session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to update session metadata: {str(e)}")
            raise

    # =========================================================================
    # Deletion Operations
    # =========================================================================

    async def delete_session(self, session_id: str):
        """
        Delete session and all its messages

        Args:
            session_id: Session identifier

        Example:
            >>> await provider.delete_session("session_xyz")
        """
        collection = await self._get_collection()

        try:
            result = await collection.delete_one({"session_id": session_id})

            if result.deleted_count > 0:
                logger.info(f"Deleted session: {session_id}")
            else:
                logger.warning(f"Session not found for deletion: {session_id}")

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            raise

    async def delete_user_sessions(self, user_id: str):
        """
        Delete all sessions for a user

        Args:
            user_id: User identifier

        Returns:
            Number of sessions deleted

        Example:
            >>> deleted_count = await provider.delete_user_sessions("user_123")
        """
        collection = await self._get_collection()

        try:
            result = await collection.delete_many({"user_id": user_id})
            deleted_count = result.deleted_count

            logger.info(f"Deleted {deleted_count} sessions for user: {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete user sessions: {str(e)}")
            return 0

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session

        Args:
            session_id: Session identifier

        Returns:
            Dict with stats (message_count, user_messages, assistant_messages, etc.)
        """
        session = await self.get_session(session_id)

        if not session:
            return {}

        messages = session.get('messages', [])

        stats = {
            "session_id": session_id,
            "total_messages": len(messages),
            "user_messages": sum(1 for m in messages if m['role'] == 'user'),
            "assistant_messages": sum(1 for m in messages if m['role'] == 'assistant'),
            "created_at": session.get('created_at'),
            "updated_at": session.get('updated_at'),
            "file_ids": session.get('file_ids', [])
        }

        return stats

    async def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Singleton instance for dependency injection
_chat_history_provider_instance: Optional[ChatHistoryProvider] = None


async def get_chat_history_provider() -> ChatHistoryProvider:
    """
    FastAPI dependency for Chat History Provider (Singleton)

    Usage in endpoints:
        @router.post("/chat")
        async def chat(
            chat_history: ChatHistoryProvider = Depends(get_chat_history_provider)
        ):
            ...
    """
    global _chat_history_provider_instance

    if _chat_history_provider_instance is None:
        _chat_history_provider_instance = ChatHistoryProvider()

    return _chat_history_provider_instance
