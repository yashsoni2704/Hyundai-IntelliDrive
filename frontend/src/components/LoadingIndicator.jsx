export default function LoadingIndicator() {
  return (
    <div className="message-row message-row--bot">
      <div className="message-bubble message-bubble--bot message-bubble--loading">
        <div className="loading-content">
          <span>Searching knowledge base...</span>
          <span className="typing-indicator">
            <span />
            <span />
            <span />
          </span>
        </div>
      </div>
    </div>
  )
}
