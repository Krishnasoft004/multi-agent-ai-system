"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Send,
  Bot,
  User,
  CheckCircle,
  Clock,
  AlertCircle,
  Brain,
  Search,
  FileText,
  Database,
  Wifi,
  WifiOff,
  Play,
  BarChart3,
} from "lucide-react"

interface AgentEvent {
  type: string
  agent?: string
  message?: string
  timestamp: string
  plan?: Task[]
  task?: Task
  results?: string
  summary?: string
  completed_tasks?: number
  total_tasks?: number
  internal?: boolean // NEW: Flag for internal events
}

interface Task {
  id: string
  type: string
  description: string
  status: "pending" | "in_progress" | "completed" | "failed"
  priority?: number
  estimated_time?: number
  created_at?: string
  started_at?: string
  completed_at?: string
  results?: string
}

interface Message {
  role: string
  content: string
  timestamp: string
  agent?: string
  type?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function MultiAgentSystem() {
  const [sessionId, setSessionId] = useState<string>("")
  const [messages, setMessages] = useState<Message[]>([])
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([])
  const [currentPlan, setCurrentPlan] = useState<Task[]>([])
  const [completedTasks, setCompletedTasks] = useState<Task[]>([])
  const [inputMessage, setInputMessage] = useState("")
  const [isConnected, setIsConnected] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [connectionError, setConnectionError] = useState<string>("")
  const [backendStatus, setBackendStatus] = useState<any>(null)
  const [executionProgress, setExecutionProgress] = useState(0)
  const eventSourceRef = useRef<EventSource | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Add these new state variables after the existing ones
  const [sessionHistory, setSessionHistory] = useState<any[]>([])

  useEffect(() => {
    checkBackendHealth()
    initializeSession()
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, agentEvents])

  useEffect(() => {
    // Calculate execution progress
    const totalTasks = currentPlan.length + completedTasks.length
    if (totalTasks > 0) {
      const progress = (completedTasks.length / totalTasks) * 100
      setExecutionProgress(progress)
    } else {
      setExecutionProgress(0)
    }
  }, [currentPlan, completedTasks])

  // Add this useEffect after the existing ones
  useEffect(() => {
    if (sessionId) {
      loadSessionHistory(sessionId)
    }
  }, [sessionId])

  // Update the checkBackendHealth function
  const checkBackendHealth = async () => {
    try {
      console.log(`🔍 Checking backend health at: ${API_BASE}`)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000) // 15 second timeout

      const response = await fetch(`${API_BASE}/health`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        const status = await response.json()
        setBackendStatus(status)
        setConnectionError("")
        console.log("✅ Backend health check successful:", status)

        // Also test the main endpoint
        const mainResponse = await fetch(`${API_BASE}/`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        })

        if (mainResponse.ok) {
          const mainStatus = await mainResponse.json()
          console.log("✅ Main endpoint also working:", mainStatus)
        }
      } else {
        const errorText = await response.text()
        setConnectionError(`Backend health check failed: ${response.status} - ${errorText}`)
        console.error("❌ Backend health check failed:", response.status, errorText)
      }
    } catch (error: any) {
      let errorMessage = "Cannot connect to backend"

      if (error.name === "AbortError") {
        errorMessage = `Backend timeout - no response from ${API_BASE} after 15 seconds`
      } else if (error.message?.includes("fetch")) {
        errorMessage = `Network error - is backend running at ${API_BASE}?`
      } else if (error.message?.includes("ECONNREFUSED")) {
        errorMessage = `Connection refused - backend not responding at ${API_BASE}`
      } else {
        errorMessage = `Connection failed: ${error.message}`
      }

      setConnectionError(errorMessage)
      console.error("❌ Backend health check failed:", error)
      console.log("🔍 Troubleshooting steps:")
      console.log("1. Check if backend container is running: docker-compose ps")
      console.log("2. Check backend logs: docker-compose logs -f backend")
      console.log("3. Check if port 8000 is accessible: curl http://localhost:8000/health")
      console.log("4. Restart services: docker-compose restart")
      console.log(`5. Backend URL being used: ${API_BASE}`)
    }
  }

  // Add retry logic to initializeSession
  const initializeSession = async (retryCount = 0) => {
    try {
      console.log(`🚀 Starting new session... (attempt ${retryCount + 1})`)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 20000) // 20 second timeout

      const response = await fetch(`${API_BASE}/session/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      setSessionId(data.session_id)
      setConnectionError("")
      console.log("✅ Session created:", data.session_id)
      connectToEventStream(data.session_id)
    } catch (error: any) {
      let errorMessage = "Failed to start session"

      if (error.name === "AbortError") {
        errorMessage = "Session creation timeout - backend may be starting up"
      } else if (error.message?.includes("fetch")) {
        errorMessage = "Network error during session creation"
      } else {
        errorMessage = `Session creation failed: ${error.message}`
      }

      console.error(`❌ Failed to start session (attempt ${retryCount + 1}):`, error)

      // Retry logic for session creation
      if (retryCount < 3) {
        console.log(`🔄 Retrying session creation in ${(retryCount + 1) * 2} seconds...`)
        setTimeout(
          () => {
            initializeSession(retryCount + 1)
          },
          (retryCount + 1) * 2000,
        )
      } else {
        setConnectionError(errorMessage)
      }
    }
  }

  const connectToEventStream = (sessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      console.log("🔌 Connecting to event stream for session:", sessionId)
      const eventSource = new EventSource(`${API_BASE}/session/${sessionId}/stream`)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setIsConnected(true)
        setConnectionError("")
        console.log("✅ SSE connection established")
      }

      eventSource.onmessage = (event) => {
        try {
          const data: AgentEvent = JSON.parse(event.data)
          handleAgentEvent(data)
        } catch (error) {
          console.error("❌ Failed to parse SSE event:", error)
        }
      }

      eventSource.onerror = (error) => {
        console.error("❌ SSE connection error:", error)
        setIsConnected(false)
        setConnectionError("Real-time connection lost - attempting reconnect...")

        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          if (sessionId && !eventSourceRef.current?.readyState) {
            console.log("🔄 Attempting SSE reconnection...")
            connectToEventStream(sessionId)
          }
        }, 3000)
      }
    } catch (error) {
      console.error("❌ Failed to create SSE connection:", error)
      setConnectionError("Failed to establish real-time connection")
    }
  }

  // FIXED: Filter out internal keepalive events from UI
  const handleAgentEvent = (event: AgentEvent) => {
    // Skip internal events (like keepalive) from showing in UI
    if (event.internal || event.type === "keepalive") {
      console.log("🔄 Keepalive received (hidden from UI)")
      return
    }

    console.log("📡 Received event:", event.type, event.message?.slice(0, 50))
    setAgentEvents((prev) => [...prev, event])

    switch (event.type) {
      case "agent_thinking":
      case "agent_working":
      case "agent_start":
      case "agent_delegation":
        // Real-time event feed population
        console.log(`🤖 ${event.agent}: ${event.message}`)
        break

      case "plan_created":
        if (event.plan) {
          console.log("📋 Plan created with", event.plan.length, "tasks")
          setCurrentPlan(event.plan)
          setCompletedTasks([]) // Reset completed tasks for new plan
          setExecutionProgress(0) // Reset progress

          // Add plan creation message to chat
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `📋 **Plan Created**: ${event.plan.length} tasks scheduled for execution`,
              timestamp: event.timestamp,
              agent: "coordinator",
              type: "plan_update",
            },
          ])
        }
        break

      case "task_started":
        if (event.task) {
          console.log("🚀 Task started:", event.task.description)
          // Update current plan with task status
          setCurrentPlan((prev) =>
            prev.map((task) =>
              task.id === event.task?.id
                ? { ...task, status: "in_progress" as const, started_at: event.timestamp }
                : task,
            ),
          )

          // Add task start message to chat
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `🚀 **Task Started**: ${event.task.description}`,
              timestamp: event.timestamp,
              agent: event.agent || "system",
              type: "task_update",
            },
          ])
        }
        break

      case "task_updated":
        if (event.task) {
          console.log("📝 Task updated:", event.task.id, event.task.status)
          setCurrentPlan((prev) => prev.map((task) => (task.id === event.task?.id ? { ...event.task } : task)))
        }
        break

      case "agent_complete":
        if (event.task) {
          console.log("✅ Agent completed:", event.agent, event.task.description)

          // Move completed task from current plan to completed tasks
          setCompletedTasks((prev) => {
            const exists = prev.some((task) => task.id === event.task?.id)
            if (!exists) {
              const updatedTask = { ...event.task!, status: "completed" as const, completed_at: event.timestamp }
              return [...prev, updatedTask]
            }
            return prev
          })

          // Remove from current plan
          setCurrentPlan((prev) => prev.filter((task) => task.id !== event.task?.id))

          // Add completion message to chat with results preview
          const resultPreview = event.results ? event.results.slice(0, 100) + "..." : ""
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `✅ **${event.agent?.replace("_", " ").toUpperCase()} COMPLETED**\n\n${event.message}\n\n${resultPreview ? `**Preview**: ${resultPreview}` : ""}`,
              timestamp: event.timestamp,
              agent: event.agent || "system",
              type: "agent_completion",
            },
          ])
        }
        break

      case "final_response":
        console.log("🎯 Final response received")
        setIsProcessing(false)
        if (event.message) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: event.message!,
              timestamp: event.timestamp,
              agent: "coordinator",
              type: "final_response",
            },
          ])
        }

        // Update session history
        loadSessionHistory(sessionId)
        break

      case "error":
        console.error("❌ Error event:", event.message)
        setIsProcessing(false)
        setConnectionError(event.message || "Unknown error occurred")

        // Add error message to chat
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `❌ **Error**: ${event.message}`,
            timestamp: event.timestamp,
            agent: "system",
            type: "error",
          },
        ])
        break
    }
  }

  // Add session management functions after the existing functions:
  const loadSessionHistory = async (sessionId: string) => {
    try {
      const response = await fetch(`${API_BASE}/session/${sessionId}/history`)
      if (response.ok) {
        const history = await response.json()
        setSessionHistory(history.conversations || [])

        // Load previous messages if any
        if (history.session_data?.messages) {
          setMessages(history.session_data.messages)
        }
      }
    } catch (error) {
      console.error("Failed to load session history:", error)
    }
  }

  // Update the sendMessage function to immediately show user input in chat:

  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId || isProcessing) return

    const userMessageText = inputMessage.trim()
    console.log("📤 Sending message:", userMessageText)

    setIsProcessing(true)
    setConnectionError("")

    // Clear previous execution state
    setAgentEvents([])
    setCurrentPlan([])
    setCompletedTasks([])
    setExecutionProgress(0)

    // Add user message immediately to chat interface
    const userMessage: Message = {
      role: "user",
      content: userMessageText,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Add processing indicator to chat
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content:
          "🤖 **Processing your request...** \n\nCoordinator is analyzing your input and creating an execution plan.",
        timestamp: new Date().toISOString(),
        agent: "coordinator",
        type: "processing",
      },
    ])

    try {
      const response = await fetch(`${API_BASE}/session/${sessionId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessageText }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      console.log("✅ Message sent successfully")
      setInputMessage("")
    } catch (error) {
      console.error("❌ Failed to send message:", error)
      setConnectionError(`Failed to send message: ${error}`)
      setIsProcessing(false)

      // Remove processing message and add error
      setMessages((prev) =>
        prev.slice(0, -1).concat([
          {
            role: "assistant",
            content: `❌ **Failed to send message**: ${error}`,
            timestamp: new Date().toISOString(),
            agent: "system",
            type: "error",
          },
        ]),
      )
    }
  }

  const retryConnection = () => {
    setConnectionError("")
    checkBackendHealth()
    if (!sessionId) {
      initializeSession()
    }
  }

  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case "coordinator":
        return <Brain className="h-4 w-4" />
      case "search_agent":
        return <Search className="h-4 w-4" />
      case "analysis_agent":
        return <BarChart3 className="h-4 w-4" />
      case "summary_agent":
        return <FileText className="h-4 w-4" />
      case "memory_agent":
        return <Database className="h-4 w-4" />
      default:
        return <Bot className="h-4 w-4" />
    }
  }

  const getAgentColor = (agent: string) => {
    const colors: Record<string, string> = {
      coordinator: "bg-blue-100 text-blue-800 border-blue-200",
      search_agent: "bg-green-100 text-green-800 border-green-200",
      analysis_agent: "bg-yellow-100 text-yellow-800 border-yellow-200",
      summary_agent: "bg-purple-100 text-purple-800 border-purple-200",
      memory_agent: "bg-orange-100 text-orange-800 border-orange-200",
    }
    return colors[agent] || "bg-gray-100 text-gray-800 border-gray-200"
  }

  const getTaskStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "in_progress":
        return <Play className="h-4 w-4 text-blue-500 animate-pulse" />
      case "failed":
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getTaskTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      search: "bg-green-50 border-green-200 text-green-700",
      research: "bg-green-50 border-green-200 text-green-700",
      analysis: "bg-yellow-50 border-yellow-200 text-yellow-700",
      summary: "bg-purple-50 border-purple-200 text-purple-700",
      memory: "bg-orange-50 border-orange-200 text-orange-700",
    }
    return colors[type] || "bg-gray-50 border-gray-200 text-gray-700"
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Enhanced Header with Session Management */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-4xl font-bold text-gray-900">Multi-Agent AI System</h1>
            {/* Remove the extra buttons - keep it simple */}
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <Badge variant={isConnected ? "default" : "destructive"} className="px-3 py-1">
              {isConnected ? <Wifi className="h-3 w-3 mr-1" /> : <WifiOff className="h-3 w-3 mr-1" />}
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>

            {sessionId && <span className="text-sm text-gray-500">Session: {sessionId.slice(0, 8)}...</span>}

            {isProcessing && (
              <Badge variant="secondary" className="animate-pulse">
                🤖 Agents Working...
              </Badge>
            )}

            {backendStatus && (
              <div className="flex gap-2">
                <Badge variant={backendStatus.mongodb_connected ? "default" : "secondary"}>
                  DB: {backendStatus.mongodb_connected ? "Connected" : "Memory"}
                </Badge>
                <Badge variant={backendStatus.openai_configured ? "default" : "secondary"}>
                  AI: {backendStatus.openai_configured ? "Enabled" : "Demo"}
                </Badge>
              </div>
            )}
          </div>

          {/* Enhanced Connection Error Display */}
          {connectionError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="h-5 w-5 text-red-500" />
                <span className="text-red-700 font-medium">Connection Issue</span>
              </div>
              <p className="text-red-600 text-sm">{connectionError}</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Enhanced Chat Interface with better message display */}
          <div className="lg:col-span-2">
            <Card className="h-[700px] flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-blue-500" />
                  Chat Interface
                  {isProcessing && (
                    <Badge variant="secondary" className="animate-pulse ml-2">
                      🤖 Processing...
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <ScrollArea className="flex-1 pr-4">
                  <div className="space-y-4">
                    {/* Enhanced Welcome Message */}
                    {messages.length === 0 && agentEvents.length === 0 && (
                      <div className="text-center py-8">
                        <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Multi-Agent AI System Ready</h3>

                        {!sessionId ? (
                          <div className="mb-4">
                            <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                            <p className="text-gray-500">Connecting to backend...</p>
                          </div>
                        ) : connectionError ? (
                          <div className="mb-4">
                            <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
                            <p className="text-red-500">Connection failed</p>
                          </div>
                        ) : (
                          <div className="mb-4">
                            <p className="text-gray-500 mb-4">
                              Send a message and watch the agents coordinate in real-time!
                            </p>
                            <div className="text-sm text-gray-400 space-y-1 bg-gray-50 p-4 rounded-lg">
                              <p className="font-medium text-gray-600">Try these examples:</p>
                              <p>"Research artificial intelligence trends and create a summary"</p>
                              <p>"Analyze the benefits of remote work"</p>
                              <p>"Explain quantum computing and its applications"</p>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Enhanced Message Display */}
                    {messages.map((message, index) => (
                      <div key={`msg-${index}`} className="flex gap-3">
                        <div className="flex-shrink-0 mt-1">
                          {message.role === "user" ? (
                            <User className="h-6 w-6 text-blue-500" />
                          ) : (
                            <div className="flex items-center">
                              {message.agent && getAgentIcon(message.agent)}
                              {!message.agent && <Bot className="h-6 w-6 text-green-500" />}
                            </div>
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm">
                              {message.role === "user"
                                ? "You"
                                : message.agent
                                  ? message.agent.replace("_", " ").toUpperCase()
                                  : "AI Assistant"}
                            </span>
                            {message.agent && message.agent !== "system" && (
                              <Badge className={`text-xs ${getAgentColor(message.agent)}`}>
                                {message.agent.replace("_", " ")}
                              </Badge>
                            )}
                            <span className="text-xs text-gray-500">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </span>
                            {message.type && (
                              <Badge variant="outline" className="text-xs">
                                {message.type.replace("_", " ")}
                              </Badge>
                            )}
                          </div>
                          <div
                            className={`rounded-lg p-4 border shadow-sm ${
                              message.role === "user"
                                ? "bg-blue-50 border-blue-200"
                                : message.type === "error"
                                  ? "bg-red-50 border-red-200"
                                  : message.type === "processing"
                                    ? "bg-yellow-50 border-yellow-200"
                                    : "bg-white"
                            }`}
                          >
                            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div ref={messagesEndRef} />
                </ScrollArea>

                <Separator className="my-4" />

                {/* Enhanced Input Area */}
                <div className="space-y-2">
                  {/* Connection Status Bar */}
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center gap-2">
                      {isConnected ? (
                        <>
                          <Wifi className="h-3 w-3 text-green-500" /> Connected
                        </>
                      ) : (
                        <>
                          <WifiOff className="h-3 w-3 text-red-500" /> Disconnected
                        </>
                      )}
                      {sessionId && <span>• Session: {sessionId.slice(0, 8)}...</span>}
                    </div>
                    {isProcessing && <span className="text-blue-500 animate-pulse">Agents working...</span>}
                  </div>

                  <div className="flex gap-2">
                    <Input
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      placeholder={
                        !sessionId
                          ? "Connecting..."
                          : connectionError
                            ? "Fix connection to continue..."
                            : "Ask the AI agents anything..."
                      }
                      onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                      disabled={isProcessing || !isConnected || !sessionId || !!connectionError}
                      className="flex-1"
                    />
                    <Button
                      onClick={sendMessage}
                      disabled={isProcessing || !isConnected || !sessionId || !inputMessage.trim() || !!connectionError}
                      size="icon"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Real-time Event Feed */}
          {/* Enhanced Real-time Event Feed */}
          <div className="lg:col-span-1">
            <Card className="h-[700px] flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5 text-green-500" />
                  Real-Time Agent Feed
                  {agentEvents.length > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {agentEvents.length} events
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <ScrollArea className="flex-1 pr-4">
                  <div className="space-y-2">
                    {agentEvents.length === 0 ? (
                      <div className="text-center py-8">
                        <Bot className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-500">No agent activity yet</p>
                        <p className="text-xs text-gray-400 mt-1">Send a message to see agents in action</p>
                      </div>
                    ) : (
                      agentEvents.map((event, index) => (
                        <div
                          key={`feed-${index}`}
                          className={`p-3 rounded border text-xs transition-all duration-200 ${
                            event.type === "agent_thinking"
                              ? "bg-blue-50 border-blue-200"
                              : event.type === "agent_working"
                                ? "bg-yellow-50 border-yellow-200"
                                : event.type === "agent_start"
                                  ? "bg-green-50 border-green-200"
                                  : event.type === "agent_complete"
                                    ? "bg-emerald-50 border-emerald-200"
                                    : event.type === "plan_created"
                                      ? "bg-purple-50 border-purple-200"
                                      : event.type === "task_started"
                                        ? "bg-orange-50 border-orange-200"
                                        : event.type === "error"
                                          ? "bg-red-50 border-red-200"
                                          : "bg-gray-50 border-gray-200"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            {event.agent && getAgentIcon(event.agent)}
                            {event.agent && (
                              <Badge className={`text-xs ${getAgentColor(event.agent)}`}>
                                {event.agent.replace("_", " ")}
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-xs">
                              {event.type.replace("_", " ")}
                            </Badge>
                            <span className="text-xs text-gray-500 ml-auto">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-gray-700 font-medium">{event.message}</p>

                          {/* Show additional event details */}
                          {event.type === "plan_created" && event.plan && (
                            <div className="mt-2 text-xs text-blue-600 bg-blue-100 p-2 rounded">
                              📋 Plan: {event.plan.length} tasks created
                              <div className="mt-1 space-y-1">
                                {event.plan.slice(0, 3).map((task, i) => (
                                  <div key={i} className="text-xs">
                                    {i + 1}. {task.type}: {task.description.slice(0, 40)}...
                                  </div>
                                ))}
                                {event.plan.length > 3 && (
                                  <div className="text-xs text-blue-500">+{event.plan.length - 3} more tasks...</div>
                                )}
                              </div>
                            </div>
                          )}

                          {event.type === "agent_complete" && event.results && (
                            <div className="mt-2 text-xs text-green-600 bg-green-100 p-2 rounded max-h-20 overflow-y-auto">
                              <strong>Results:</strong> {event.results.slice(0, 150)}...
                            </div>
                          )}

                          {event.type === "task_started" && event.task && (
                            <div className="mt-2 text-xs text-orange-600 bg-orange-100 p-2 rounded">
                              🚀 Task: {event.task.description}
                              {event.task.estimated_time && (
                                <span className="ml-2">• Est: {event.task.estimated_time}s</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Task Planning Sidebar */}
          <div className="space-y-6">
            {/* Session History Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-5 w-5 text-purple-500" />
                  Session Logs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[200px]">
                  <div className="space-y-2">
                    {messages.filter((m) => m.role === "user").length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">No messages yet</p>
                    ) : (
                      messages
                        .filter((m) => m.role === "user")
                        .map((msg, index) => (
                          <div key={index} className="p-2 bg-gray-50 rounded border">
                            <p className="text-xs text-gray-600 mb-1">{new Date(msg.timestamp).toLocaleString()}</p>
                            <p className="text-sm font-medium">{msg.content}</p>
                          </div>
                        ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Current Plan */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-5 w-5 text-blue-500" />
                  Current Plan ({currentPlan.length} tasks)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {currentPlan.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No active tasks</p>
                  ) : (
                    currentPlan.map((task, index) => (
                      <div key={task.id} className={`p-3 rounded-lg border ${getTaskTypeColor(task.type)}`}>
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0 mt-0.5">{getTaskStatusIcon(task.status)}</div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="text-xs">
                                {task.type}
                              </Badge>
                              <span className="text-xs text-gray-500">#{index + 1}</span>
                              {task.priority && (
                                <Badge variant="secondary" className="text-xs">
                                  P{task.priority}
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm font-medium mb-1">{task.description}</p>
                            <div className="flex items-center gap-2 text-xs text-gray-600">
                              <span className="capitalize">Status: {task.status.replace("_", " ")}</span>
                              {task.estimated_time && <span>• Est: {task.estimated_time}s</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Completed Tasks */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  Completed Tasks ({completedTasks.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[300px]">
                  <div className="space-y-3">
                    {completedTasks.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">No completed tasks yet</p>
                    ) : (
                      completedTasks.map((task) => (
                        <div key={task.id} className="p-3 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-start gap-3">
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge variant="outline" className="text-xs">
                                  {task.type}
                                </Badge>
                                {task.completed_at && (
                                  <span className="text-xs text-gray-500">
                                    {new Date(task.completed_at).toLocaleTimeString()}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm font-medium mb-1">{task.description}</p>
                              {task.results && (
                                <p className="text-xs text-gray-600 bg-white p-2 rounded border mt-2">{task.results}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
