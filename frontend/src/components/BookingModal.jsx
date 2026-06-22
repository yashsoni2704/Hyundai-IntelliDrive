import { useCallback, useEffect, useState } from 'react'
import {
  createBooking,
  fetchBookingDates,
  fetchMyBookings,
  fetchSlotsForDate,
} from '../services/api'

export default function BookingModal({ isOpen, onClose, vehicleModel = 'General', onBooked }) {
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [slots, setSlots] = useState([])
  const [selectedSlot, setSelectedSlot] = useState('')
  const [vehicle, setVehicle] = useState(vehicleModel)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(null)
  const [myBookings, setMyBookings] = useState([])
  const [success, setSuccess] = useState(null)

  const loadDates = useCallback(async () => {
    try {
      const data = await fetchBookingDates()
      setDates(data.dates)
      if (data.dates.length > 0) setSelectedDate(data.dates[0])
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const loadBookings = useCallback(async () => {
    try {
      const data = await fetchMyBookings()
      setMyBookings(data.bookings)
    } catch {
      setMyBookings([])
    }
  }, [])

  const loadSlots = useCallback(async (date) => {
    if (!date) return
    setLoading(true)
    setError('')
    try {
      const data = await fetchSlotsForDate(date)
      setSlots(data.slots)
      setSelectedSlot('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isOpen) return
    setSuccess(null)
    setConflict(null)
    setError('')
    loadDates()
    loadBookings()
  }, [isOpen, loadDates, loadBookings])

  useEffect(() => {
    if (selectedDate) loadSlots(selectedDate)
  }, [selectedDate, loadSlots])

  useEffect(() => {
    setVehicle(vehicleModel)
  }, [vehicleModel])

  const handleBook = async () => {
    if (!selectedDate || !selectedSlot) {
      setError('Please select a date and time slot')
      return
    }
    setLoading(true)
    setError('')
    setConflict(null)
    try {
      const result = await createBooking({
        date: selectedDate,
        time_slot: selectedSlot,
        vehicle_model: vehicle,
      })
      setSuccess(result)
      loadBookings()
      loadSlots(selectedDate)
      onBooked?.(result)
    } catch (err) {
      if (err.status === 409 && err.data?.detail) {
        setConflict(err.data.detail)
      } else {
        setError(typeof err.data?.detail === 'string' ? err.data.detail : err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const applySuggestedSlot = () => {
    if (!conflict?.next_available_date || !conflict?.next_available_slot) return
    setSelectedDate(conflict.next_available_date)
    setSelectedSlot(conflict.next_available_slot)
    setConflict(null)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card booking-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Book a test drive</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div className="modal-body">
          {success && (
            <div className="booking-success">
              <p>{success.message}</p>
              <p className="booking-success-detail">
                {success.date} · {success.slot_label} · {success.vehicle_model}
              </p>
            </div>
          )}

          {error && <p className="form-error">{error}</p>}

          {conflict && (
            <div className="booking-conflict">
              <p><strong>{conflict.message}</strong></p>
              <p>Requested: {conflict.requested_date} at {conflict.requested_label}</p>
              {conflict.next_available_date && (
                <>
                  <p>
                    Next free slot: {conflict.next_available_date} at {conflict.next_available_label}
                  </p>
                  <button type="button" className="btn-secondary" onClick={applySuggestedSlot}>
                    Use suggested slot
                  </button>
                </>
              )}
            </div>
          )}

          <div className="booking-form">
            <label>
              Vehicle
              <input type="text" value={vehicle} onChange={(e) => setVehicle(e.target.value)} />
            </label>

            <label>
              Date
              <select value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}>
                {dates.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </label>

            <div className="slot-section">
              <p className="slot-label">Time slot (1 hour each)</p>
              {loading && slots.length === 0 ? (
                <p className="panel-muted">Loading slots...</p>
              ) : (
                <div className="slot-grid">
                  {slots.map((slot) => (
                    <button
                      key={slot.time}
                      type="button"
                      disabled={!slot.available}
                      className={[
                        'slot-btn',
                        selectedSlot === slot.time ? 'slot-btn--selected' : '',
                        !slot.available ? 'slot-btn--taken' : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => setSelectedSlot(slot.time)}
                    >
                      {slot.label}
                      {!slot.available && <span className="slot-taken-tag">Taken</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              className="btn-primary"
              onClick={handleBook}
              disabled={loading || !selectedSlot}
            >
              {loading ? 'Booking...' : 'Confirm booking'}
            </button>
          </div>

          {myBookings.length > 0 && (
            <div className="my-bookings-section">
              <h3>Your bookings</h3>
              <ul className="bookings-list">
                {myBookings.map((b) => (
                  <li key={b.id}>
                    <span>{b.date}</span>
                    <span>{b.slot_label}</span>
                    <span>{b.vehicle_model}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
