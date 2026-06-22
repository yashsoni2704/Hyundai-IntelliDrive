import { useCallback, useEffect, useState } from 'react'

function chatStorageKey(userId) {
  return userId ? `hyundai_chat_${userId}` : 'hyundai_chat_guest'
}

function loadConversations(userId) {
  try {
    const raw = localStorage.getItem(chatStorageKey(userId))
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveConversations(userId, conversations) {
  localStorage.setItem(chatStorageKey(userId), JSON.stringify(conversations))
}

function createConversation(title = 'New Chat') {
  return {
    id: crypto.randomUUID(),
    title,
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
}

export function useChatHistory(userId) {
  const sessionKey = userId || 'guest'
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)

  // Reload conversations when user session changes
  useEffect(() => {
    const saved = loadConversations(sessionKey)
    setConversations(saved)
    setActiveId(saved[0]?.id ?? null)
  }, [sessionKey])

  useEffect(() => {
    if (conversations.length > 0 || activeId) {
      saveConversations(sessionKey, conversations)
    }
  }, [conversations, sessionKey, activeId])

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null

  const startNewChat = useCallback(() => {
    const chat = createConversation()
    setConversations((prev) => [chat, ...prev])
    setActiveId(chat.id)
    return chat.id
  }, [])

  const selectConversation = useCallback((id) => {
    setActiveId(id)
  }, [])

  const clearAllHistory = useCallback(() => {
    setConversations([])
    setActiveId(null)
    localStorage.removeItem(chatStorageKey(sessionKey))
  }, [sessionKey])

  const addMessage = useCallback((role, content, meta = {}) => {
    setConversations((prev) => {
      let next = [...prev]
      let targetId = activeId

      if (!targetId || !next.find((c) => c.id === targetId)) {
        const chat = createConversation(
          role === 'user' ? content.slice(0, 40) : 'New Chat',
        )
        next = [chat, ...next]
        targetId = chat.id
        setActiveId(targetId)
      }

      return next.map((c) => {
        if (c.id !== targetId) return c
        const messages = [
          ...c.messages,
          { id: crypto.randomUUID(), role, content, ...meta, timestamp: Date.now() },
        ]
        const title =
          c.messages.length === 0 && role === 'user'
            ? content.slice(0, 40) + (content.length > 40 ? '...' : '')
            : c.title
        return {
          ...c,
          title,
          messages,
          updatedAt: Date.now(),
        }
      })
    })
  }, [activeId])

  const ensureActiveConversation = useCallback(() => {
    if (!activeId || !conversations.find((c) => c.id === activeId)) {
      return startNewChat()
    }
    return activeId
  }, [activeId, conversations, startNewChat])

  return {
    conversations,
    activeConversation,
    activeId,
    startNewChat,
    selectConversation,
    clearAllHistory,
    addMessage,
    ensureActiveConversation,
  }
}
