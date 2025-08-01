from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
import os

# Try to import MongoDB, fall back to in-memory storage
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

class MemoryStore:
    def __init__(self):
        self.logger = logging.getLogger("memory_store")
        self.mongodb_client = None
        self.db = None
        self.collection = None
        
        # In-memory fallback
        self.memory_data = {}
        
        # Try to connect to MongoDB
        self._init_mongodb()
    
    async def initialize(self):
        """Initialize the memory store (async version of __init__ setup)"""
        # This method is called from FastAPI startup
        # The actual initialization is already done in __init__
        self.logger.info("Memory store initialization completed")
        return True

    async def close(self):
        """Close database connections"""
        if self.mongodb_client:
            self.mongodb_client.close()
            self.logger.info("💾 MEMORY_STORE - MongoDB connection closed")
    
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        if not MONGODB_AVAILABLE:
            self.logger.warning("MongoDB not available, using in-memory storage")
            return
        
        try:
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            self.mongodb_client = MongoClient(mongodb_url)
            self.db = self.mongodb_client.multi_agent_system
            self.collection = self.db.sessions
            
            # Test connection
            self.mongodb_client.admin.command('ping')
            self.logger.info("MongoDB connected successfully")
            
        except Exception as e:
            self.logger.warning(f"MongoDB connection failed: {e}, using in-memory storage")
            self.mongodb_client = None
    
    @property
    def connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self.mongodb_client is not None

    def is_connected(self) -> bool:
        """Alternative method to check connection status"""
        try:
            if self.mongodb_client:
                self.mongodb_client.admin.command('ping')
                return True
            return False
        except Exception:
            return False
    
    def create_session(self, session_id: str, initial_data: Dict[str, Any] = None) -> bool:
        """Create a new session"""
        try:
            session_data = {
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'messages': [],
                'tasks': [],
                'context': initial_data or {}
            }
            
            if self.mongodb_client:
                # MongoDB storage
                result = self.collection.insert_one(session_data)
                success = result.inserted_id is not None
            else:
                # In-memory storage
                self.memory_data[session_id] = session_data
                success = True
            
            if success:
                self.logger.info(f"Session created: {session_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Session creation error: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            if self.mongodb_client:
                # MongoDB storage
                session = self.collection.find_one({'session_id': session_id})
                if session:
                    session.pop('_id', None)  # Remove MongoDB ID
                return session
            else:
                # In-memory storage
                return self.memory_data.get(session_id)
                
        except Exception as e:
            self.logger.error(f"Session retrieval error: {e}")
            return None
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            if self.mongodb_client:
                # MongoDB storage
                result = self.collection.update_one(
                    {'session_id': session_id},
                    {'$set': update_data}
                )
                success = result.modified_count > 0
            else:
                # In-memory storage
                if session_id in self.memory_data:
                    self.memory_data[session_id].update(update_data)
                    success = True
                else:
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Session update error: {e}")
            return False
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add a message to session history"""
        try:
            message['timestamp'] = datetime.now().isoformat()
            
            if self.mongodb_client:
                # MongoDB storage
                result = self.collection.update_one(
                    {'session_id': session_id},
                    {
                        '$push': {'messages': message},
                        '$set': {'updated_at': datetime.now().isoformat()}
                    }
                )
                success = result.modified_count > 0
            else:
                # In-memory storage
                if session_id in self.memory_data:
                    self.memory_data[session_id]['messages'].append(message)
                    self.memory_data[session_id]['updated_at'] = datetime.now().isoformat()
                    success = True
                else:
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Message addition error: {e}")
            return False
    
    def add_task(self, session_id: str, task: Dict[str, Any]) -> bool:
        """Add a task to session"""
        try:
            task['timestamp'] = datetime.now().isoformat()
            task['status'] = task.get('status', 'pending')
            
            if self.mongodb_client:
                # MongoDB storage
                result = self.collection.update_one(
                    {'session_id': session_id},
                    {
                        '$push': {'tasks': task},
                        '$set': {'updated_at': datetime.now().isoformat()}
                    }
                )
                success = result.modified_count > 0
            else:
                # In-memory storage
                if session_id in self.memory_data:
                    self.memory_data[session_id]['tasks'].append(task)
                    self.memory_data[session_id]['updated_at'] = datetime.now().isoformat()
                    success = True
                else:
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Task addition error: {e}")
            return False
    
    def update_task_status(self, session_id: str, task_id: str, status: str, result: Dict[str, Any] = None) -> bool:
        """Update task status"""
        try:
            if self.mongodb_client:
                # MongoDB storage
                update_query = {
                    '$set': {
                        'tasks.$.status': status,
                        'tasks.$.updated_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                }
                if result:
                    update_query['$set']['tasks.$.result'] = result
                
                result = self.collection.update_one(
                    {'session_id': session_id, 'tasks.id': task_id},
                    update_query
                )
                success = result.modified_count > 0
            else:
                # In-memory storage
                if session_id in self.memory_data:
                    for task in self.memory_data[session_id]['tasks']:
                        if task.get('id') == task_id:
                            task['status'] = status
                            task['updated_at'] = datetime.now().isoformat()
                            if result:
                                task['result'] = result
                            success = True
                            break
                    else:
                        success = False
                    
                    if success:
                        self.memory_data[session_id]['updated_at'] = datetime.now().isoformat()
                else:
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Task status update error: {e}")
            return False
    
    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get complete session history"""
        try:
            session = self.get_session(session_id)
            if not session:
                return {
                    'session_id': session_id,
                    'messages': [],
                    'tasks': [],
                    'context': {}
                }
            
            return {
                'session_id': session_id,
                'messages': session.get('messages', []),
                'tasks': session.get('tasks', []),
                'context': session.get('context', {}),
                'created_at': session.get('created_at'),
                'updated_at': session.get('updated_at')
            }
            
        except Exception as e:
            self.logger.error(f"History retrieval error: {e}")
            return {
                'session_id': session_id,
                'messages': [],
                'tasks': [],
                'context': {},
                'error': str(e)
            }
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions"""
        try:
            if self.mongodb_client:
                # MongoDB storage
                sessions = list(self.collection.find(
                    {},
                    {'session_id': 1, 'created_at': 1, 'updated_at': 1, '_id': 0}
                ).sort('updated_at', -1).limit(limit))
            else:
                # In-memory storage
                sessions = []
                for session_id, data in self.memory_data.items():
                    sessions.append({
                        'session_id': session_id,
                        'created_at': data.get('created_at'),
                        'updated_at': data.get('updated_at')
                    })
                sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
                sessions = sessions[:limit]
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Session listing error: {e}")
            return []

# Global memory store instance
memory_store = MemoryStore()
