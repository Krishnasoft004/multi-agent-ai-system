from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import json
from memory.store import MemoryStore

@dataclass
class Session:
    session_id: str
    created_at: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    user_id: Optional[str] = None

class SessionManager:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.active_sessions: Dict[str, Session] = {}
        self.event_queues: Dict[str, asyncio.Queue] = {}
    
    async def create_session(self, session_id: str) -> Session:
        """Create a new session"""
        session = Session(
            session_id=session_id,
            created_at=datetime.now()
        )
        self.active_sessions[session_id] = session
        self.event_queues[session_id] = asyncio.Queue()
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get existing session"""
        return self.active_sessions.get(session_id)
    
    async def add_message(self, session_id: str, role: str, content: str):
        """Add message to session"""
        if session_id in self.active_sessions:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            self.active_sessions[session_id].messages.append(message)
    
    async def emit_event(self, session_id: str, event: Dict[str, Any]):
        """Emit event to session subscribers"""
        if session_id in self.event_queues:
            await self.event_queues[session_id].put(event)
    
    async def subscribe_to_events(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to session events"""
        if session_id not in self.event_queues:
            self.event_queues[session_id] = asyncio.Queue()
        
        queue = self.event_queues[session_id]
        
        try:
            while True:
                # Wait for event with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"type": "keepalive", "timestamp": datetime.now().isoformat()}
        except asyncio.CancelledError:
            pass
