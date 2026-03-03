"use client"

import type { UIMessage } from "ai"

// DESKTOP MODE: Chat endpoint moved to FastAPI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function sendChatMessage(messages: UIMessage[]) {
  try {
    const response = await fetch(`${API_BASE}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages }),
    })

    if (!response.ok) {
      throw new Error("Failed to send message")
    }

    return response
  } catch (error) {
    console.error("[v0] Chat error:", error)
    throw error
  }
}
