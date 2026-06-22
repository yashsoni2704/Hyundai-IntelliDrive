import MessageBubble from './MessageBubble'
import WelcomeScreen from './WelcomeScreen'
import LoadingIndicator from './LoadingIndicator'

export default function ChatArea({
  messages,
  isLoading,
  onSuggestionClick,
  onSuggestionAction,
  isAuthenticated,
  onBookSlot,
  onLoginRequired,
}) {
  return (
    <div className="chat-area">
      <div className="chat-messages">
        {messages.length === 0 && !isLoading && (
          <WelcomeScreen onSuggestionClick={onSuggestionClick} />
        )}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onSuggestionAction={onSuggestionAction}
            isAuthenticated={isAuthenticated}
            onBookSlot={onBookSlot}
            onLoginRequired={onLoginRequired}
          />
        ))}
        {isLoading && <LoadingIndicator />}
      </div>
    </div>
  )
}
