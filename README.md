# Multi-Agent AI System

A sophisticated multi-agent AI system built with FastAPI, Next.js, and LangGraph that coordinates multiple specialized AI agents to handle complex tasks.

## 🎯 Features

- **Multi-Agent Coordination**: Coordinator agent creates execution plans and manages other agents
- **Specialized Agents**: Search, Summary, Memory, and Analysis agents with specific capabilities
- **Real-time Updates**: Server-Sent Events (SSE) for live task progress and agent communication
- **Task Planner UI**: Visual representation of task execution and status
- **Session Management**: Persistent conversations with MongoDB storage
- **Multiple LLM Support**: OpenAI, Google Gemini, and Groq integration

## 🏗️ Architecture

### Backend (FastAPI)
- **Coordinator Agent**: Creates execution plans and manages workflow
- **Search Agent**: Performs web searches and information gathering
- **Summary Agent**: Creates comprehensive summaries and synthesizes information
- **Memory Agent**: Manages conversation context and session memory
- **Analysis Agent**: Provides detailed analysis and insights

### Frontend (Next.js)
- **Chat Interface**: Real-time conversation with AI agents
- **Task Planner**: Visual task execution tracking
- **Event Feed**: Live updates from agent activities
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- API key for at least one LLM provider (OpenAI, Google Gemini, or Groq)
- 4GB RAM minimum
- Internet connection for LLM APIs

### 1. Clone and Setup

\`\`\`bash
git clone <repository>
cd multi-agent-system
\`\`\`

### 2. Configure Environment

\`\`\`bash
# Copy environment template
cp .env.example .env

# Add your API keys
nano .env
\`\`\`

Add your API keys:
\`\`\`env
GOOGLE_API_KEY=your_google_gemini_key_here
# OR
OPENAI_API_KEY=your_openai_key_here  
# OR
GROQ_API_KEY=your_groq_key_here
\`\`\`

### 3. Start the System

\`\`\`bash
# Start all services
docker-compose up --build

# Access the application
open http://localhost:3000
\`\`\`

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📡 API Endpoints

### Session Management
- `POST /session/start` - Create new session
- `POST /session/{id}/message` - Send message to session
- `GET /session/{id}/history` - Get conversation history
- `GET /session/{id}/stream` - SSE stream for real-time updates

### Health & Status
- `GET /` - Basic health check
- `GET /health` - Detailed system status
- `GET /ping` - Simple ping endpoint

## 🤖 Agent System

### Coordinator Agent
- Analyzes user requests and creates execution plans
- Delegates tasks to specialized sub-agents
- Coordinates overall workflow

### Search Agent
- Information gathering and research
- Provides comprehensive search results
- Handles knowledge retrieval tasks

### Summary Agent
- Analysis and summarization of findings
- Creates comprehensive reports
- Provides strategic insights

### Memory Agent
- Stores conversation history and context
- Manages session-specific information
- Provides context for future interactions

### Analysis Agent
- Detailed analysis of data
- Provides insights and recommendations

## 🎨 Frontend Features

### Chat Interface
- Real-time messaging with AI agents
- Message history and session management
- Connection status indicators

### Task Planner UI
- Visual representation of task execution and status
- Live task status updates
- Progress tracking for multi-step workflows

### Agent Activity Feed
- Live stream of agent thoughts and actions
- Real-time event updates via SSE
- Agent-specific activity tracking

### Session Support
- Resume previous conversations
- View complete chat and task logs
- Persistent session management

## 🛠️ Development

### Local Development

#### Backend
\`\`\`bash
cd backend
pip install -r requirements.txt
python main.py
\`\`\`

#### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

### Environment Variables

#### Required API Keys (at least one)
- `OPENAI_API_KEY` - OpenAI API key
- `GROQ_API_KEY` - Groq API key (free tier available)
- `GOOGLE_API_KEY` - Google Gemini API key

#### Optional
- `MONGODB_URL` - MongoDB connection string (defaults to local)
- `HOST` - Server host (defaults to 0.0.0.0)
- `PORT` - Server port (defaults to 8000)
- `NEXT_PUBLIC_API_URL` - Public API URL (defaults to http://localhost:8000)

### Monitoring

#### Logs
\`\`\`bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f frontend
\`\`\`

#### Service Status
\`\`\`bash
# Check service status
docker-compose ps

# Restart services
docker-compose restart
\`\`\`

## 📊 Sample Session

1. **User**: "Research artificial intelligence applications"
2. **Coordinator**: Creates plan with search → summary → memory tasks
3. **Search Agent**: Researches AI applications and trends
4. **Summary Agent**: Analyzes findings and creates comprehensive report
5. **Memory Agent**: Stores conversation context for future reference
6. **Analysis Agent**: Provides detailed analysis of the report
7. **Frontend**: Shows real-time progress and final results

## 🔧 Troubleshooting

### Common Issues

1. **Frontend build fails**: Check package.json dependencies
2. **Backend API errors**: Verify API keys in .env file
3. **MongoDB connection**: Ensure MongoDB service is running
4. **SSE connection issues**: Check CORS and proxy settings

### Logs
\`\`\`bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f frontend
\`\`\`

## 📝 Success Criteria

✅ **Multi-agent flow**: Coordinator plans, delegates, and aggregates  
✅ **SSE feedback**: Agent logs stream in real-time  
✅ **UI responsiveness**: Task planner and agent activity visible  
✅ **Memory persistence**: Chat and structured data recalled  
✅ **Developer UX**: Clean, modular, documented codebase  

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details
