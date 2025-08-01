# backend/db/dbutils.py
from backend.db.db import messages_collection, sessions_collection, tasks_collection, agent_outputs_collection
from datetime import datetime

# Save chat message
async def log_message(session_id: str, role: str, content: str):
    message_doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    await messages_collection.insert_one(message_doc)


# Save agent task output (used by agents)
async def save_agent_output_to_db(session_id: str, agent_name: str, task_id: str, output_data: dict):
    agent_output_doc = {
        "session_id": session_id,
        "agent_name": agent_name,
        "task_id": task_id,
        "output": output_data,
        "timestamp": datetime.utcnow()
    }
    await agent_outputs_collection.insert_one(agent_output_doc)


# Save session info
async def create_session(session_id: str):
    session_doc = {
        "session_id": session_id,
        "created_at": datetime.utcnow()
    }
    await sessions_collection.insert_one(session_doc)


# Save task metadata
async def save_task(session_id: str, task: dict):
    task_doc = {
        "session_id": session_id,
        "task": task,
        "created_at": datetime.utcnow()
    }
    await tasks_collection.insert_one(task_doc)
