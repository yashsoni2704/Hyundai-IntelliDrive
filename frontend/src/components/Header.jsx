import { useAuth } from '../contexts/AuthContext'

export default function Header({ onToggleSidebar, onOpenAuth, onOpenBookings }) {
  const { user, logout, isAuthenticated } = useAuth()

  return (
    <header className="chat-header">
      <button
        type="button"
        className="icon-btn mobile-menu-btn"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M3 6H21M3 12H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
      <div className="header-text">
        <h1>Hyundai Knowledge Assistant</h1>
        <p>Semantic Search Powered by ChromaDB</p>
      </div>
      <div className="header-actions">
        {isAuthenticated ? (
          <>
            <button type="button" className="header-btn" onClick={onOpenBookings}>
              My bookings
            </button>
            <span className="header-user">{user.full_name || user.email}</span>
            <button type="button" className="header-btn header-btn--ghost" onClick={logout}>
              Sign out
            </button>
          </>
        ) : (
          <button type="button" className="header-btn header-btn--accent" onClick={onOpenAuth}>
            Sign in
          </button>
        )}
      </div>
    </header>
  )
}
