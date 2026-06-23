import { useCallback, useEffect, useState } from 'react'
import {
  endChatSession,
  fetchRecentExchanges,
  fetchSessionMessages,
  startChatSession,
} from '../services/api'

const SESSION_KEY = 'hyundai_chat_session_id'
const SESSION_USER_KEY = 'hyundai_chat_user_id'

export function useSessionChat(userId, isAuthenticated) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [pastExchanges, setPastExchanges] = useState([])
  const [viewingPastId, setViewingPastId] = useState(null)
  const [loadingSession, setLoadingSession] = useState(false)

  const viewingPast = pastExchanges.find((e) => e.id === viewingPastId) ?? null

  const refreshRecent = useCallback(async () => {
    if (!isAuthenticated) {
      setPastExchanges([])
      return
    }
    try {
      const data = await fetchRecentExchanges()
      setPastExchanges(data.exchanges || [])
    } catch {
      setPastExchanges([])
    }
  }, [isAuthenticated])

  const initSession = useCallback(async () => {
    if (!isAuthenticated || !userId) {
      setSessionId(null)
      setMessages([])
      setViewingPastId(null)
      setPastExchanges([])
      return
    }

    setLoadingSession(true)
    setViewingPastId(null)
    try {
      const data = await startChatSession()
      setSessionId(data.session_id)
      sessionStorage.setItem(SESSION_KEY, data.session_id)
      sessionStorage.setItem(SESSION_USER_KEY, userId)
      setMessages([])

      const recent = await fetchRecentExchanges()
      setPastExchanges(recent.exchanges || [])
    } catch {
      setSessionId(null)
      setMessages([])
    } finally {
      setLoadingSession(false)
    }
  }, [isAuthenticated, userId])

  const restoreSessionIfNeeded = useCallback(async () => {
    if (!isAuthenticated || !userId) return

    const storedId = sessionStorage.getItem(SESSION_KEY)
    const storedUser = sessionStorage.getItem(SESSION_USER_KEY)
    if (!storedId || storedUser !== userId) {
      await initSession()
      return
    }

    setLoadingSession(true)
    try {
      const data = await fetchSessionMessages(storedId)
      setSessionId(storedId)
      setMessages(data.messages || [])
      const recent = await fetchRecentExchanges()
      setPastExchanges(recent.exchanges || [])
    } catch {
      sessionStorage.removeItem(SESSION_KEY)
      sessionStorage.removeItem(SESSION_USER_KEY)
      await initSession()
    } finally {
      setLoadingSession(false)
    }
  }, [isAuthenticated, userId, initSession])

  useEffect(() => {
    if (isAuthenticated && userId) {
      restoreSessionIfNeeded()
    } else {
      setSessionId(null)
      setMessages([])
      setPastExchanges([])
      setViewingPastId(null)
      sessionStorage.removeItem(SESSION_KEY)
      sessionStorage.removeItem(SESSION_USER_KEY)
    }
  }, [userId, isAuthenticated, restoreSessionIfNeeded])

  const endSession = useCallback(async () => {
    const sid = sessionId || sessionStorage.getItem(SESSION_KEY)
    if (sid && isAuthenticated) {
      try {
        await endChatSession(sid)
      } catch {
        /* ignore */
      }
    }
    sessionStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setViewingPastId(null)
  }, [sessionId, isAuthenticated])

  const addMessage = useCallback((role, content, meta = {}) => {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role,
        content,
        ...meta,
        timestamp: Date.now(),
      },
    ])
  }, [])

  const selectPastExchange = useCallback((id) => {
    setViewingPastId(id)
  }, [])

  const backToCurrentChat = useCallback(() => {
    setViewingPastId(null)
  }, [])

  return {
    sessionId,
    messages,
    pastExchanges,
    viewingPast,
    viewingPastId,
    loadingSession,
    addMessage,
    refreshRecent,
    selectPastExchange,
    backToCurrentChat,
    endSession,
    initSession,
  }
}
