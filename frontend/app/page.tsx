"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Send, Bot, User, Wifi, WifiOff, Loader2 } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: string
}

interface Event {
  type: string
  agent?: string
  message?: string
  timestamp: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function MultiAgentChat() {
  const [sessionId, setSessionId] = useState<string>("")
  const [messages, setMessages] = useState<Message[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState("")

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const [tasks, setTasks] = useState<any[]>([])
  const [sessionLogs, setSessionLogs] = useState<Message[]>([])
  const [completedTasks, setCompletedTasks] = useState<any[]>([])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, events])

  useEffect(() => {
    initializeSession()
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const initializeSession = async () => {
    try {
      console.log("🚀 Starting session...")
      const response = await fetch(`${API_BASE}/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_context: {} }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      setSessionId(data.session_id)
      setConnectionError("")
      console.log("✅ Session created:", data.session_id)

      // Start SSE connection
      connectToEventStream(data.session_id)
    } catch (error: any) {
      console.error("❌ Session creation failed:", error)
      setConnectionError(`Failed to start session: ${error.message}`)
    }
  }

  const connectToEventStream = (sessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      console.log("🔌 Connecting to event stream...")
      const eventSource = new EventSource(`${API_BASE}/session/${sessionId}/stream`)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setIsConnected(true)
        setConnectionError("")
        console.log("✅ SSE connected")
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log("📡 Event received:", data.type)

          if (data.type === "keepalive") return

          setEvents((prev) => [...prev, data])

          // Handle different event types
          if (data.type === "plan_created" && data.plan) {
            setTasks(data.plan)
          }

          if (data.type === "task_started" && data.task) {
            setTasks((prev) => prev.map((task) => (task.id === data.task.id ? { ...task, status: "running" } : task)))
          }

          if (data.type === "task_completed" && data.task) {
            setTasks((prev) => prev.map((task) => (task.id === data.task.id ? { ...task, status: "completed" } : task)))
            setCompletedTasks((prev) => [...prev, data.task])
          }

          if (data.type === "final_response" && data.message) {
            const assistantMessage = {
              role: "assistant" as const,
              content: data.message,
              timestamp: data.timestamp,
            }
            setMessages((prev) => [...prev, assistantMessage])
            setSessionLogs((prev) => [...prev, assistantMessage])
            setIsLoading(false)
          }
        } catch (error) {
          console.error("❌ Failed to parse event:", error)
        }
      }

      eventSource.onerror = (error) => {
        console.error("❌ SSE error:", error)
        setIsConnected(false)
        setConnectionError("Connection lost")
      }
    } catch (error) {
      console.error("❌ Failed to create SSE:", error)
      setConnectionError("Failed to establish connection")
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setSessionLogs((prev) => [...prev, userMessage])
    setIsLoading(true)
    setConnectionError("")

    // Reset tasks for new request
    setTasks([])
    setCompletedTasks([])

    try {
      const response = await fetch(`${API_BASE}/session/${sessionId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input.trim() }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      setInput("")
      console.log("✅ Message sent")
    } catch (error: any) {
      console.error("❌ Failed to send message:", error)
      setConnectionError(`Failed to send message: ${error.message}`)
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Multi-Agent AI System</h1>
          <div className="flex items-center gap-4">
            <Badge variant={isConnected ? "default" : "destructive"}>
              {isConnected ? <Wifi className="h-3 w-3 mr-1" /> : <WifiOff className="h-3 w-3 mr-1" />}
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
            {sessionId && <span className="text-sm text-gray-500">Session: {sessionId.slice(0, 8)}...</span>}
          </div>
          {connectionError && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {connectionError}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Interface */}
          <div className="lg:col-span-2">
            <Card className="h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  Chat Interface
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col p-0">
                <ScrollArea className="flex-1 p-4">
                  <div className="space-y-4">
                    {messages.length === 0 && (
                      <div className="text-center py-8">
                        <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Multi-Agent AI Ready</h3>
                        <p className="text-gray-500">Send a message to start!</p>
                      </div>
                    )}

                    {messages.map((message, index) => (
                      <div key={index} className="flex gap-3">
                        <div className="flex-shrink-0 mt-1">
                          {message.role === "user" ? (
                            <User className="h-6 w-6 text-blue-500" />
                          ) : (
                            <Bot className="h-6 w-6 text-green-500" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm">
                              {message.role === "user" ? "You" : "AI Assistant"}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div
                            className={`rounded-lg p-3 ${
                              message.role === "user" ? "bg-blue-50 border border-blue-200" : "bg-white border"
                            }`}
                          >
                            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>

                <Separator />

                <div className="p-4">
                  <div className="flex gap-2">
                    <Input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder={
                        !sessionId
                          ? "Connecting..."
                          : connectionError
                            ? "Fix connection to continue..."
                            : "Ask me anything..."
                      }
                      disabled={isLoading || !isConnected || !sessionId || !!connectionError}
                      className="flex-1"
                    />
                    <Button
                      onClick={sendMessage}
                      disabled={isLoading || !isConnected || !sessionId || !input.trim() || !!connectionError}
                      size="icon"
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Event Feed */}
          <div>
            <Card className="h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle className="text-lg">Real-Time Events</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col p-0">
                <ScrollArea className="flex-1 p-4">
                  <div className="space-y-2">
                    {events.length === 0 ? (
                      <div className="text-center py-8">
                        <Bot className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-500">No events yet</p>
                      </div>
                    ) : (
                      events.slice(-10).map((event, index) => (
                        <div key={index} className="p-3 bg-gray-50 rounded border text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <Badge variant="outline" className="text-xs">
                              {event.type}
                            </Badge>
                            <span className="text-gray-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
                          </div>
                          {event.message && <p className="text-gray-700">{event.message}</p>}
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Task Planning Sidebar */}
          <div className="space-y-4">
            {/* Session Logs */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Session Logs</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-32">
                  <div className="space-y-2">
                    {sessionLogs.filter((m) => m.role === "user").length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">No messages yet</p>
                    ) : (
                      sessionLogs
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
              <CardHeader>
                <CardTitle className="text-lg">Current Plan ({tasks.length} tasks)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {tasks.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No active tasks</p>
                  ) : (
                    tasks.map((task, index) => (
                      <div key={task.id} className="p-3 rounded-lg border bg-blue-50">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">
                            {task.type}
                          </Badge>
                          <span className="text-xs text-gray-500">#{index + 1}</span>
                          <Badge
                            variant={
                              task.status === "completed"
                                ? "default"
                                : task.status === "running"
                                  ? "secondary"
                                  : "outline"
                            }
                            className="text-xs"
                          >
                            {task.status}
                          </Badge>
                        </div>
                        <p className="text-sm font-medium">{task.description}</p>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Completed Tasks */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Completed Tasks ({completedTasks.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-40">
                  <div className="space-y-2">
                    {completedTasks.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">No completed tasks yet</p>
                    ) : (
                      completedTasks.map((task) => (
                        <div key={task.id} className="p-3 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {task.type}
                            </Badge>
                            <span className="text-xs text-gray-500">
                              {new Date(task.completed_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-sm font-medium">{task.description}</p>
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
