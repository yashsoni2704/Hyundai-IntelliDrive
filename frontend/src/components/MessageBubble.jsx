import FollowUpSuggestions from './FollowUpSuggestions'
import SlotTable from './SlotTable'

export default function MessageBubble({
  message,
  onSuggestionAction,
  isAuthenticated,
  onBookSlot,
  onLoginRequired,
}) {
  const isUser = message.role === 'user'
  const isLoading = message.loading
  const isError = message.error
  const isSlots = message.response_type === 'slots'

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--bot'}`}>
      <div className="message-block">
        <div
          className={[
            'message-bubble',
            isUser ? 'message-bubble--user' : 'message-bubble--bot',
            isError ? 'message-bubble--error' : '',
            isLoading ? 'message-bubble--loading' : '',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          {isLoading ? (
            <div className="loading-content">
              <span>Searching knowledge base...</span>
              <span className="typing-indicator">
                <span />
                <span />
                <span />
              </span>
            </div>
          ) : (
            <p>{message.content}</p>
          )}
        </div>

        {!isUser && !isLoading && isSlots && message.available_slots?.length > 0 && (
          <SlotTable
            slots={message.available_slots}
            isAuthenticated={isAuthenticated}
            onBookSlot={onBookSlot}
            onLoginRequired={onLoginRequired}
          />
        )}

        {!isUser && !isLoading && message.suggestions?.length > 0 && (
          <FollowUpSuggestions
            suggestions={message.suggestions}
            onAction={onSuggestionAction}
          />
        )}
      </div>
    </div>
  )
}
