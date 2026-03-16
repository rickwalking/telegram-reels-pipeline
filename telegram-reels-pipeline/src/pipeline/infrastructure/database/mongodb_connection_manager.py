"""MongoDB connection lifecycle manager."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

_DEFAULT_DATABASE_NAME = "telegram_reels_pipeline"
_DEFAULT_MAX_POOL_SIZE = 10
_DEFAULT_SERVER_SELECTION_TIMEOUT_MS = 5000


class MongoDbConnectionManager:
    """Manages MongoDB connection lifecycle.

    Wraps Motor async client and ODMantic AIOEngine. Callers must call
    ``connect()`` before accessing the engine property and ``disconnect()``
    on shutdown.
    """

    def __init__(self, connection_string: str, database_name: str = _DEFAULT_DATABASE_NAME) -> None:
        """Initialise with connection parameters but do not open the connection yet."""
        self._connection_string = connection_string
        self._database_name = database_name
        self._motor_client: AsyncIOMotorClient[dict[str, object]] | None = None
        self._odmantic_engine: AIOEngine | None = None

    async def connect(self) -> AIOEngine:
        """Open the MongoDB connection and return the ODMantic engine."""
        self._motor_client = AsyncIOMotorClient(
            self._connection_string,
            maxPoolSize=_DEFAULT_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=_DEFAULT_SERVER_SELECTION_TIMEOUT_MS,
        )
        self._odmantic_engine = AIOEngine(client=self._motor_client, database=self._database_name)
        return self._odmantic_engine

    async def disconnect(self) -> None:
        """Close the MongoDB connection and release resources."""
        if self._motor_client is not None:
            self._motor_client.close()
            self._motor_client = None
            self._odmantic_engine = None

    async def health_check(self) -> bool:
        """Ping MongoDB to verify the connection is alive."""
        if self._motor_client is None:
            return False
        try:
            await self._motor_client.admin.command("ping")
            return True
        except Exception:
            return False

    @property
    def engine(self) -> AIOEngine:
        """Return the active ODMantic engine.

        Raises ``RuntimeError`` if ``connect()`` has not been called.
        """
        if self._odmantic_engine is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._odmantic_engine
