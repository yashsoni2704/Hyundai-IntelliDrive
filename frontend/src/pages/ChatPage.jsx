/**
 * Main chat page — orchestrates the entire user chat experience.
 *
 * State sources:
 *   useAuth — logged-in user + JWT
 *   useSessionChat — session ID, messages, sidebar recent Q&As
 *   useSuggestionTracker — which suggestion chips were already clicked
 *
 * Flow: user types → handleSend → sendChatMessage API → display answer + suggestions
 * Guests use local guestMessages; logged-in users use server session + DB logs.
 */
import { useCallback, useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'
import ChatArea from '../components/ChatArea'
import ChatInput from '../components/ChatInput'
import KnowledgePanel from '../components/KnowledgePanel'
import AuthModal from '../components/AuthModal'
import BookingModal from '../components/BookingModal'
import PastExchangeView from '../components/PastExchangeView'
import { useAuth } from '../contexts/AuthContext'
import { useSessionChat } from '../hooks/useSessionChat'
import { useSuggestionTracker } from '../hooks/useSuggestionTracker'
import { sendChatMessage, fetchStats, createBooking } from '../services/api'

export default function ChatPage() {
  const { user, isAuthenticated, logout } = useAuth()
  const userId = user?.id ?? null
  const {
    sessionId,
    messages: sessionMessages,
    pastExchanges,
    viewingPast,
    viewingPastId,
    loadingSession,
    addMessage: addSessionMessage,
    refreshRecent,
    selectPastExchange,
    backToCurrentChat,
    endSession,
  } = useSessionChat(userId, isAuthenticated)
  const { markUsed, getUsedIds } = useSuggestionTracker(userId)

  const [guestMessages, setGuestMessages] = useState([])
  const [guestContext, setGuestContext] = useState(() => {
    try {
      const raw = sessionStorage.getItem('hyundai_guest_context')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
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

  const messages = isAuthenticated ? sessionMessages : guestMessages
  const addMessage = isAuthenticated ? addSessionMessage : (role, content, meta = {}) => {
    setGuestMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, content, ...meta, timestamp: Date.now() },
    ])
  }

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

  const handleLogout = useCallback(async () => {
    await endSession()
    logout()
  }, [endSession, logout])

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
      if (!message || isLoading || viewingPastId) return

      if (suggestionItem) {
        markUsed(suggestionItem)
      }

      setInput('')
      addMessage('user', message)
      setIsLoading(true)

      try {
        const result = await sendChatMessage(
          message,
          getUsedIds(),
          isAuthenticated ? sessionId : null,
          isAuthenticated ? null : guestContext,
        )
        addMessage('assistant', result.answer, {
          found: result.found,
          response_type: result.response_type || 'faq',
          available_slots: result.available_slots || [],
          suggestions: result.suggestions || [],
        })
        if (!isAuthenticated && result.context) {
          setGuestContext(result.context)
          sessionStorage.setItem('hyundai_guest_context', JSON.stringify(result.context))
        }
        if (isAuthenticated) {
          await refreshRecent()
        }
      } catch (error) {
        const errorMessage = error.message || 'Unable to connect to the knowledge base. Please try again.'
        addMessage('assistant', errorMessage, { error: true })
      } finally {
        setIsLoading(false)
      }
    },
    [
      input,
      isLoading,
      viewingPastId,
      addMessage,
      getUsedIds,
      markUsed,
      isAuthenticated,
      sessionId,
      guestContext,
      refreshRecent,
    ],
  )

  const handleBookingComplete = useCallback((result) => {
    addMessage(
      'assistant',
      `Your test drive is confirmed for ${result.date} at ${result.slot_label} (${result.vehicle_model}).`,
      { suggestions: [{ label: 'View my bookings', action: 'my_bookings', id: 'my_bookings' }] },
    )
  }, [addMessage])

  const handleBookSlot = useCallback(
    async (slot) => {
      if (!isAuthenticated) {
        addMessage('assistant', 'Please login first to book a test drive slot.', {
          suggestions: [{ label: 'Sign in', action: 'login', id: 'login' }],
        })
        setShowAuth(true)
        return
      }

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
    [isAuthenticated, bookingVehicle, addMessage, handleBookingComplete],
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
        pastExchanges={isAuthenticated ? pastExchanges : []}
        viewingPastId={viewingPastId}
        onSelectPastExchange={(id) => {
          selectPastExchange(id)
          setSidebarOpen(false)
        }}
        onBackToCurrentChat={() => {
          backToCurrentChat()
          setSidebarOpen(false)
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
          onLogout={handleLogout}
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

          {viewingPast ? (
            <PastExchangeView exchange={viewingPast} onBack={backToCurrentChat} />
          ) : (
            <ChatArea
              messages={messages}
              isLoading={isLoading || loadingSession}
              onSuggestionClick={(text) => handleSend(text)}
              onSuggestionAction={handleSuggestionAction}
              isAuthenticated={isAuthenticated}
              onBookSlot={handleBookSlot}
              onLoginRequired={handleLoginRequired}
            />
          )}

          {!viewingPast && (
            <ChatInput
              value={input}
              onChange={setInput}
              onSend={() => handleSend()}
              disabled={isLoading || loadingSession}
            />
          )}
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
