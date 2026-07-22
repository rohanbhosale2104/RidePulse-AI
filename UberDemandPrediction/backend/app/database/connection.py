"""
MongoDB connection management using Motor (async driver).
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger("uvicorn")


class MongoManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    async def connect(self):
        logger.info("Connecting to MongoDB at %s ...", settings.MONGO_URI)
        self.client = AsyncIOMotorClient(settings.MONGO_URI, uuidRepresentation="standard")
        self.db = self.client[settings.MONGO_DB_NAME]
        # Fail fast if the server is unreachable
        await self.client.admin.command("ping")
        await self._ensure_indexes()
        logger.info("MongoDB connection established. Database: %s", settings.MONGO_DB_NAME)

    async def _ensure_indexes(self):
        await self.db["users"].create_index("username", unique=True)
        await self.db["users"].create_index("email", unique=True)
        await self.db["predictions"].create_index("user_id")
        await self.db["predictions"].create_index("created_at")

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    def get_db(self) -> AsyncIOMotorDatabase:
        return self.db


mongo_manager = MongoManager()


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency to retrieve the active database instance."""
    return mongo_manager.get_db()
