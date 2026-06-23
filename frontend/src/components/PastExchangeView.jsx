import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

export default function PastExchangeView({ exchange, onBack }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [exchange])

  if (!exchange) return null

  const userMsg = {
    id: `${exchange.id}-q`,
    role: 'user',
    content: exchange.query,
  }
  const botMsg = {
    id: exchange.id,
    role: 'assistant',
    content: exchange.answer,
    found: exchange.found,
    response_type: exchange.response_type,
  }

  return (
    <div className="past-exchange-view">
      <div className="past-exchange-banner">
        <button type="button" className="btn-link" onClick={onBack}>
          ← Back to current chat
        </button>
        <span className="past-exchange-label">Previous conversation · {exchange.created_at}</span>
      </div>
      <div className="chat-area" ref={scrollRef}>
        <MessageBubble message={userMsg} />
        <MessageBubble message={botMsg} />
      </div>
    </div>
  )
}
