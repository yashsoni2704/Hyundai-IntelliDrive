const SUGGESTIONS = [
  'What is the price of Hyundai Creta?',
  'Which Hyundai SUV is best for families?',
  'Does Hyundai offer electric vehicles?',
  'Can I schedule a test drive?',
  'What are available timings for today?',
]

export default function WelcomeScreen({ onSuggestionClick }) {
  return (
    <div className="welcome-screen">
      <h2 className="welcome-title">Welcome to Hyundai Knowledge Assistant</h2>
      <p className="welcome-subtitle">Try asking:</p>
      <ul className="welcome-suggestions">
        {SUGGESTIONS.map((text) => (
          <li key={text}>
            <button
              type="button"
              className="suggestion-btn"
              onClick={() => onSuggestionClick(text)}
            >
              {text}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
