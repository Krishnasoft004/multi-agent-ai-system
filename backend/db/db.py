# backend/db/db.py
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "multi_agent_ai")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

# Export collections
sessions_collection = db["sessions"]
messages_collection = db["messages"]
tasks_collection = db["tasks"]
agent_outputs_collection = db["agent_outputs"]  #  New collection for agent logs
