"use client"

import type { UIMessage } from "ai"

export async function sendChatMessage(messages: UIMessage[]) {
  try {
    const response = await fetch("/api/research/chat", {
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
