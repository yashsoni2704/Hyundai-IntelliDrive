import { useCallback, useEffect, useRef, useState } from 'react'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'
import ChatArea from '../components/ChatArea'
import ChatInput from '../components/ChatInput'
import KnowledgePanel from '../components/KnowledgePanel'
import AuthModal from '../components/AuthModal'
import BookingModal from '../components/BookingModal'
import { useAuth } from '../contexts/AuthContext'
import { useChatHistory } from '../hooks/useChatHistory'
import { useSuggestionTracker } from '../hooks/useSuggestionTracker'
import { sendChatMessage, fetchStats, createBooking } from '../services/api'

export default function ChatPage() {
  const { user, isAuthenticated } = useAuth()
  const userId = user?.id ?? null
  const {
    conversations,
    activeConversation,
    activeId,
    startNewChat,
    selectConversation,
    clearAllHistory,
    addMessage,
    ensureActiveConversation,
  } = useChatHistory(userId)
  const { markUsed, getUsedIds } = useSuggestionTracker(userId)

  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showKnowledge, setShowKnowledge] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsError, setStatsError] = useState(null)
  const [showAuth, setShowAuth] = useState(false)
  const [showBooking, setShowBooking] = useState(false)
  const [bookingVehicle, setBookingVehicle] = useState('General')
  const bottomRef = useRef(null)

  const messages = activeConversation?.messages ?? []

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleToggleSidebar = useCallback(() => {
    const isMobile = window.matchMedia('(max-width: 768px)').matches
    if (isMobile) {
      setSidebarCollapsed(false)
      setSidebarOpen((v) => !v)
    } else {
      setSidebarOpen(false)
      setSidebarCollapsed((v) => !v)
    }
  }, [])

  const loadStats = useCallback(async () => {
    setStatsLoading(true)
    setStatsError(null)
    try {
      const data = await fetchStats()
      setStats(data)
    } catch (err) {
      setStatsError(err.message)
    } finally {
      setStatsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (showKnowledge) loadStats()
  }, [showKnowledge, loadStats])

  const requireAuth = useCallback((action) => {
    if (!isAuthenticated) {
      setShowAuth(true)
      return false
    }
    action()
    return true
  }, [isAuthenticated])

  const openBooking = useCallback((vehicle = 'General') => {
    requireAuth(() => {
      setBookingVehicle(vehicle)
      setShowBooking(true)
    })
  }, [requireAuth])

  const handleSend = useCallback(
    async (text, suggestionItem = null) => {
      const message = (text ?? input).trim()
      if (!message || isLoading) return

      if (suggestionItem) {
        markUsed(suggestionItem)
      }

      ensureActiveConversation()
      setInput('')
      addMessage('user', message)
      setIsLoading(true)

      try {
        const result = await sendChatMessage(message, getUsedIds())
        addMessage('assistant', result.answer, {
          found: result.found,
          response_type: result.response_type || 'faq',
          available_slots: result.available_slots || [],
          suggestions: result.suggestions || [],
        })
      } catch (error) {
        const errorMessage = error.message || 'Unable to connect to the knowledge base. Please try again.'
        addMessage('assistant', errorMessage, { error: true })
      } finally {
        setIsLoading(false)
      }
    },
    [input, isLoading, ensureActiveConversation, addMessage, getUsedIds, markUsed],
  )

  const handleBookingComplete = useCallback((result) => {
    ensureActiveConversation()
    addMessage(
      'assistant',
      `Your test drive is confirmed for ${result.date} at ${result.slot_label} (${result.vehicle_model}).`,
      { suggestions: [{ label: 'View my bookings', action: 'my_bookings', id: 'my_bookings' }] },
    )
  }, [ensureActiveConversation, addMessage])

  const handleBookSlot = useCallback(
    async (slot) => {
      if (!isAuthenticated) {
        addMessage('assistant', 'Please login first to book a test drive slot.', {
          suggestions: [{ label: 'Sign in', action: 'login', id: 'login' }],
        })
        setShowAuth(true)
        return
      }

      ensureActiveConversation()
      try {
        const result = await createBooking({
          date: slot.date,
          time_slot: slot.time,
          vehicle_model: bookingVehicle,
        })
        handleBookingComplete(result)
      } catch (err) {
        if (err.status === 409 && err.data?.detail) {
          const d = err.data.detail
          addMessage(
            'assistant',
            `${d.message} Next free slot: ${d.next_available_date} at ${d.next_available_label || d.next_available_slot}.`,
            { error: true },
          )
        } else {
          addMessage('assistant', err.message || 'Booking failed. Please try again.', { error: true })
        }
      }
    },
    [isAuthenticated, ensureActiveConversation, bookingVehicle, addMessage, handleBookingComplete],
  )

  const handleLoginRequired = useCallback(() => {
    addMessage('assistant', 'Please login first to book a test drive slot.', {
      suggestions: [{ label: 'Sign in', action: 'login', id: 'login' }],
    })
    setShowAuth(true)
  }, [addMessage])

  const handleSuggestionAction = useCallback(
    (item) => {
      markUsed(item)
      if (item.action === 'login') {
        setShowAuth(true)
        return
      }
      if (item.action === 'book_test_drive') {
        openBooking(item.vehicle || 'General')
        return
      }
      if (item.action === 'my_bookings') {
        requireAuth(() => setShowBooking(true))
        return
      }
      handleSend(item.query || item.label, item)
    },
    [openBooking, requireAuth, handleSend, markUsed],
  )

  return (
    <div className="app-layout">
      <Sidebar
        isOpen={sidebarOpen}
        isCollapsed={sidebarCollapsed}
        conversations={conversations}
        activeId={activeId}
        onNewChat={() => {
          startNewChat()
          setSidebarOpen(false)
        }}
        onSelectConversation={(id) => {
          selectConversation(id)
          setSidebarOpen(false)
        }}
        onClearHistory={() => {
          if (window.confirm('Clear all conversation history?')) {
            clearAllHistory()
            setSidebarOpen(false)
          }
        }}
        onToggleCollapse={handleToggleSidebar}
        onCloseMobile={() => setSidebarOpen(false)}
        onOpenKnowledge={() => setShowKnowledge((v) => !v)}
        showKnowledge={showKnowledge}
        onOpenBookings={() => requireAuth(() => setShowBooking(true))}
        isAuthenticated={isAuthenticated}
      />

      <main className={`main-content ${sidebarCollapsed ? 'main-content--expanded' : ''}`}>
        <Header
          onToggleSidebar={handleToggleSidebar}
          onOpenAuth={() => setShowAuth(true)}
          onOpenBookings={() => requireAuth(() => setShowBooking(true))}
        />

        <div className="chat-body">
          {showKnowledge && (
            <KnowledgePanel
              stats={stats}
              loading={statsLoading}
              error={statsError}
              onClose={() => setShowKnowledge(false)}
            />
          )}

          <ChatArea
            messages={messages}
            isLoading={isLoading}
            onSuggestionClick={(text) => handleSend(text)}
            onSuggestionAction={handleSuggestionAction}
            isAuthenticated={isAuthenticated}
            onBookSlot={handleBookSlot}
            onLoginRequired={handleLoginRequired}
          />
          <div ref={bottomRef} />

          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => handleSend()}
            disabled={isLoading}
          />
        </div>
      </main>

      <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
      <BookingModal
        isOpen={showBooking}
        onClose={() => setShowBooking(false)}
        vehicleModel={bookingVehicle}
        onBooked={handleBookingComplete}
      />
    </div>
  )
}
