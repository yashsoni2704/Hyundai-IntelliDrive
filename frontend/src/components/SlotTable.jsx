export default function SlotTable({ slots, isAuthenticated, onBookSlot, onLoginRequired }) {
  if (!slots?.length) return null

  return (
    <div className="slot-table-wrapper">
      <table className="slot-table">
        <thead>
          <tr>
            <th>Slot #</th>
            <th>Date</th>
            <th>Time</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {slots.map((slot) => (
            <tr key={`${slot.date}-${slot.time}`}>
              <td>{slot.slot_number}</td>
              <td>{slot.day_label}</td>
              <td>{slot.time_label}</td>
              <td>
                <button
                  type="button"
                  className="slot-book-btn"
                  onClick={() => {
                    if (!isAuthenticated) {
                      onLoginRequired(slot)
                    } else {
                      onBookSlot(slot)
                    }
                  }}
                >
                  Book
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!isAuthenticated && (
        <p className="slot-login-hint">Please login first to book a slot.</p>
      )}
    </div>
  )
}
