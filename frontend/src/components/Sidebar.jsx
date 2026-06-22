export default function Sidebar({
  isOpen,
  isCollapsed,
  conversations,
  activeId,
  onNewChat,
  onSelectConversation,
  onClearHistory,
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
          <button type="button" className="sidebar-btn sidebar-btn--primary" onClick={onNewChat}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span>New Chat</span>
          </button>
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

        <div className="sidebar-section">
          <p className="sidebar-label">Previous Conversations</p>
          <div className="conversation-list">
            {conversations.length === 0 ? (
              <p className="sidebar-empty">No conversations yet</p>
            ) : (
              conversations.map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  className={`conversation-item ${chat.id === activeId ? 'conversation-item--active' : ''}`}
                  onClick={() => onSelectConversation(chat.id)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>{chat.title}</span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="sidebar-bottom">
          <button type="button" className="sidebar-btn sidebar-btn--danger" onClick={onClearHistory}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Clear History</span>
          </button>
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
