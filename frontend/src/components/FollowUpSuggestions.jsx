export default function FollowUpSuggestions({ suggestions, onAction }) {
  if (!suggestions?.length) return null

  return (
    <div className="follow-up-suggestions">
      <p className="follow-up-label">You might also want to:</p>
      <div className="follow-up-chips">
        {suggestions.map((item, index) => (
          <button
            key={`${item.label}-${index}`}
            type="button"
            className="follow-up-chip"
            onClick={() => onAction(item)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  )
}
