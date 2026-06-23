function truncate(text, max = 42) {
  if (!text) return 'Question'
  return text.length > max ? `${text.slice(0, max)}...` : text
}

export default function Sidebar({
  isOpen,
  isCollapsed,
  pastExchanges,
  viewingPastId,
  onSelectPastExchange,
  onBackToCurrentChat,
  onToggleCollapse,
  onCloseMobile,
  onOpenKnowledge,
  showKnowledge,
  onOpenBookings,
  isAuthenticated,
}) {
  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onCloseMobile} />}
      <aside
        className={[
          'sidebar',
          isOpen ? 'sidebar--open' : '',
          isCollapsed && !isOpen ? 'sidebar--collapsed' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <div className="sidebar-top">
          {isAuthenticated && (
            <button
              type="button"
              className={`sidebar-btn ${!viewingPastId ? 'sidebar-btn--primary' : ''}`}
              onClick={onBackToCurrentChat}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>Current Chat</span>
            </button>
          )}
          <button
            type="button"
            className="sidebar-btn"
            onClick={onOpenKnowledge}
            aria-pressed={showKnowledge}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
              <path d="M12 10V16M12 7V7.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span>Knowledge Base</span>
          </button>
          {isAuthenticated && (
            <button type="button" className="sidebar-btn" onClick={onOpenBookings}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2" />
                <path d="M16 2V6M8 2V6M3 10H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>My Bookings</span>
            </button>
          )}
        </div>

        {isAuthenticated && (
          <div className="sidebar-section">
            <p className="sidebar-label">Recent Questions (last 5)</p>
            <div className="conversation-list">
              {pastExchanges.length === 0 ? (
                <p className="sidebar-empty">No previous questions yet</p>
              ) : (
                pastExchanges.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`conversation-item ${item.id === viewingPastId ? 'conversation-item--active' : ''}`}
                    onClick={() => onSelectPastExchange(item.id)}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <span>{truncate(item.query)}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        <div className="sidebar-bottom">
          <button
            type="button"
            className="icon-btn sidebar-collapse-btn"
            onClick={onToggleCollapse}
            aria-label="Collapse sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </aside>
    </>
  )
}
