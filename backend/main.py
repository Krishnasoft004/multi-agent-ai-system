import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json
import os

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from  db.db import agent_outputs_collection
import asyncio


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple in-memory storage
sessions_db = {}
active_streams = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(" MULTI-AGENT AI SYSTEM STARTUP")
    logger.info(" SYSTEM READY")
    yield
    # Shutdown
    logger.info(" SYSTEM SHUTDOWN")

# FastAPI app
app = FastAPI(
    title="Multi-Agent AI System", 
    description="Real-time multi-agent coordination", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionStartRequest(BaseModel):
    initial_context: Optional[Dict[str, Any]] = None

class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "Multi-Agent AI System",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ping")
async def ping():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "database": "memory",
            "mongodb_connected": False,
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/session/start")
async def start_session(request: SessionStartRequest):
    session_id = str(uuid.uuid4())
    
    sessions_db[session_id] = {
        'session_id': session_id,
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'tasks': []
    }
    
    logger.info(f"Session started: {session_id}")
    
    return {
        "session_id": session_id,
        "status": "started",
        "message": "Session created successfully"
    }

@app.post("/session/{session_id}/message")
async def send_message(session_id: str, request: MessageRequest, background_tasks: BackgroundTasks):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add user message
    user_message = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    }
    sessions_db[session_id]['messages'].append(user_message)
    
    # Process in background
    background_tasks.add_task(process_message, session_id, request.message)
    
    return {
        "status": "received",
        "session_id": session_id,
        "message": "Processing your request..."
    }

async def process_message(session_id: str, message: str):
    """Process message with real LLM calls"""
    try:
        # Create simulated tasks for display
        tasks = [
            {"id": "task_1", "type": "research", "description": f"Research information about: {message}", "status": "running"},
            {"id": "task_2", "type": "analysis", "description": "Analyze gathered information", "status": "pending"},
            {"id": "task_3", "type": "summary", "description": "Create comprehensive summary", "status": "pending"}
        ]
        
        # Add tasks to session
        sessions_db[session_id]['tasks'] = tasks
        
        # Emit task creation
        await emit_event(session_id, {
            "type": "plan_created",
            "plan": tasks,
            "message": f"Created execution plan with {len(tasks)} tasks",
            "timestamp": datetime.now().isoformat()
        })
        
        # Process each task
        for i, task in enumerate(tasks):
            # Update task status to running
            sessions_db[session_id]['tasks'][i]['status'] = 'running'
            
            await emit_event(session_id, {
                "type": "task_started",
                "task": task,
                "message": f"Starting: {task['description']}",
                "timestamp": datetime.now().isoformat()
            })
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Complete task
            sessions_db[session_id]['tasks'][i]['status'] = 'completed'
            sessions_db[session_id]['tasks'][i]['completed_at'] = datetime.now().isoformat()
            
            await emit_event(session_id, {
                "type": "task_completed",
                "task": sessions_db[session_id]['tasks'][i],
                "message": f"Completed: {task['description']}",
                "timestamp": datetime.now().isoformat()
            })
        
        # Get final LLM response
        response = await get_llm_response(message)
        
        # Add assistant response
        assistant_message = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        }
        sessions_db[session_id]['messages'].append(assistant_message)
        
        # Emit completion
        await emit_event(session_id, {
            "type": "final_response",
            "message": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        await emit_event(session_id, {
            "type": "error",
            "message": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

async def get_llm_response(message: str) -> str:
    """Get response from LLM"""
    try:
        # Try OpenAI first
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai_key != 'your_openai_key_here' and openai_key.startswith('sk-'):
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides comprehensive responses."},
                    {"role": "user", "content": message}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        
        # Try Groq
        groq_key = os.getenv('GROQ_API_KEY')
        if groq_key and groq_key.startswith('gsk_'):
            from groq import Groq
            client = Groq(api_key=groq_key)
            
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides comprehensive responses."},
                    {"role": "user", "content": message}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        
        # Try Google Gemini with updated model name
        google_key = os.getenv('GOOGLE_API_KEY')
        if google_key and google_key.startswith('AIza'):
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            
            # Try different model names in order of preference
            model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
            
            for model_name in model_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    full_prompt = f"You are a helpful AI assistant that provides comprehensive responses.\n\nUser: {message}"
                    response = model.generate_content(full_prompt)
                    return response.text
                except Exception as model_error:
                    logger.warning(f"Model {model_name} failed: {model_error}")
                    continue
            
            # If all models fail, raise the last error
            raise Exception("All Gemini models failed")
        
        # Fallback with better demo response
        return f"""Based on your request about "{message}", here's a comprehensive response:

This is a detailed analysis of your query. The system is working correctly but requires an API key for real AI responses.

Key points:
• The multi-agent system is functioning properly
• Real-time communication is established
• To get actual AI responses, please add your API key to the .env file

For OpenAI: OPENAI_API_KEY=sk-your-key-here
For Groq (free): GROQ_API_KEY=gsk-your-key-here
For Google: GOOGLE_API_KEY=AIza-your-key-here

The system will automatically detect and use your configured API key."""
            
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return f"I'm processing your request about: {message}. There was an error with the AI service: {str(e)}"

@app.get("/session/{session_id}/stream")
async def stream_events(session_id: str):
    """Stream real-time updates via SSE"""
    
    async def event_generator():
        # Create event queue
        event_queue = asyncio.Queue()
        
        # Add to active streams
        if session_id not in active_streams:
            active_streams[session_id] = []
        active_streams[session_id].append(event_queue)
        
        try:
            # Send connection established
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Stream events
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now().isoformat()})}\n\n"
                    
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            # Cleanup
            if session_id in active_streams and event_queue in active_streams[session_id]:
                active_streams[session_id].remove(event_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

async def emit_event(session_id: str, event_data: Dict[str, Any]):
    """Emit event to SSE streams"""
    if session_id in active_streams:
        for queue in active_streams[session_id]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Failed to emit event: {e}")

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions_db[session_id]

async def test_mongo_connection():
    await agent_outputs_collection.insert_one({
        "agent": "StartupTest",
        "status": "OK",
        "message": "This is a test insert on backend startup"
    })

asyncio.run(test_mongo_connection())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
