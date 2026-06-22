import { useCallback, useEffect, useState } from 'react'

function storageKey(userId) {
  return userId ? `hyundai_used_suggestions_${userId}` : 'hyundai_used_suggestions_guest'
}

function loadUsed(userId) {
  try {
    const raw = localStorage.getItem(storageKey(userId))
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useSuggestionTracker(userId) {
  const sessionKey = userId || 'guest'
  const [usedIds, setUsedIds] = useState([])

  useEffect(() => {
    setUsedIds(loadUsed(sessionKey))
  }, [sessionKey])

  const markUsed = useCallback((item) => {
    const id = item.id || item.label
    if (!id) return
    setUsedIds((prev) => {
      if (prev.includes(id)) return prev
      const next = [...prev, id]
      localStorage.setItem(storageKey(sessionKey), JSON.stringify(next))
      return next
    })
  }, [sessionKey])

  const getUsedIds = useCallback(() => usedIds, [usedIds])

  return { usedIds, markUsed, getUsedIds }
}
