"""MongoDB connection lifecycle manager."""

from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

_DEFAULT_DATABASE_NAME = "telegram_reels_pipeline"
_DEFAULT_MAX_POOL_SIZE = 10
_DEFAULT_SERVER_SELECTION_TIMEOUT_MS = 5000


@dataclass(frozen=True)
class MongoDbConnectionConfig:
    """Immutable configuration for a MongoDB connection."""

    connection_string: str
    database_name: str = _DEFAULT_DATABASE_NAME


class MongoDbConnectionManager:
    """Manages MongoDB connection lifecycle.

    Uses a connected/disconnected state pattern instead of nullable fields.
    Callers must call ``connect()`` before accessing the engine property.
    """

    def __init__(self, connection_config: MongoDbConnectionConfig) -> None:
        self._connection_config = connection_config
        self._is_connected = False
        self._motor_client: AsyncIOMotorClient[dict[str, object]] = AsyncIOMotorClient()
        self._odmantic_engine: AIOEngine = AIOEngine(client=self._motor_client, database=connection_config.database_name)

    async def connect(self) -> AIOEngine:
        """Open the MongoDB connection and return the ODMantic engine."""
        self._motor_client = AsyncIOMotorClient(
            self._connection_config.connection_string,
            maxPoolSize=_DEFAULT_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=_DEFAULT_SERVER_SELECTION_TIMEOUT_MS,
        )
        self._odmantic_engine = AIOEngine(client=self._motor_client, database=self._connection_config.database_name)
        self._is_connected = True
        return self._odmantic_engine

    async def disconnect(self) -> None:
        """Close the MongoDB connection and release resources."""
        if not self._is_connected:
            return
        self._motor_client.close()
        self._is_connected = False

    async def health_check(self) -> bool:
        """Ping MongoDB to verify the connection is alive."""
        if not self._is_connected:
            return False
        try:
            await self._motor_client.admin.command("ping")
        except Exception:
            return False
        return True

    @property
    def engine(self) -> AIOEngine:
        """Return the active ODMantic engine.

        Raises ``RuntimeError`` if ``connect()`` has not been called.
        """
        if not self._is_connected:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._odmantic_engine
