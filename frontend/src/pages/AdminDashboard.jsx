import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  createAdminBooking,
  deleteAdminBooking,
  fetchAdminBookings,
  fetchAdminChatLogs,
  fetchAdminDates,
  fetchAdminSlots,
  updateAdminBooking,
} from '../services/api'

const emptyForm = {
  id: '',
  customer_email: '',
  customer_name: '',
  date: '',
  time_slot: '',
  vehicle_model: 'General',
  status: 'confirmed',
}

export default function AdminDashboard() {
  const { user, logout } = useAuth()
  const [bookings, setBookings] = useState([])
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [slotData, setSlotData] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [chatLogs, setChatLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)

  const isEditing = Boolean(form.id)

  const totalBookings = bookings.length
  const uniqueUsersCount = useMemo(() => {
    return new Set(bookings.map((b) => b.customer_email.toLowerCase().trim())).size
  }, [bookings])

  const totalSlotsCapacity = useMemo(() => {
    return slotData?.slots?.length || 0
  }, [slotData])

  const remainingSlots = useMemo(() => {
    return slotData?.available_count || 0
  }, [slotData])

  const loadBookings = useCallback(async () => {
    const data = await fetchAdminBookings()
    setBookings(data.bookings || [])
  }, [])

  const loadDates = useCallback(async () => {
    const data = await fetchAdminDates()
    setDates(data.dates || [])
    if (!selectedDate && data.dates?.length) {
      setSelectedDate(data.dates[0])
      setForm((current) => ({ ...current, date: current.date || data.dates[0] }))
    }
  }, [selectedDate])

  const loadSlots = useCallback(async (date) => {
    if (!date) return
    const data = await fetchAdminSlots(date)
    setSlotData(data)
  }, [])

  const loadChatLogs = useCallback(async () => {
    setLogsLoading(true)
    try {
      const data = await fetchAdminChatLogs()
      setChatLogs(data.logs || [])
    } catch (err) {
      setError(err.message || 'Unable to load chat logs')
    } finally {
      setLogsLoading(false)
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      await Promise.all([loadBookings(), loadDates(), loadChatLogs()])
    } catch (err) {
      setError(err.message || 'Unable to load admin dashboard')
    } finally {
      setLoading(false)
    }
  }, [loadBookings, loadDates, loadChatLogs])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    loadSlots(selectedDate).catch((err) => setError(err.message || 'Unable to load slots'))
  }, [selectedDate, loadSlots])

  const availableSlotOptions = useMemo(() => {
    const slots = slotData?.slots || []
    if (!isEditing) return slots.filter((slot) => slot.available)
    return slots.filter((slot) => slot.available || slot.time === form.time_slot)
  }, [slotData, isEditing, form.time_slot])

  const resetForm = () => {
    setForm({ ...emptyForm, date: selectedDate || dates[0] || '' })
    setNotice('')
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      if (isEditing) {
        await updateAdminBooking(form.id, {
          date: form.date,
          time_slot: form.time_slot,
          vehicle_model: form.vehicle_model,
          status: form.status,
        })
        setNotice('Booking updated.')
      } else {
        await createAdminBooking({
          customer_email: form.customer_email,
          customer_name: form.customer_name,
          date: form.date,
          time_slot: form.time_slot,
          vehicle_model: form.vehicle_model,
        })
        setNotice('Booking created.')
      }
      await Promise.all([loadBookings(), loadSlots(selectedDate)])
      resetForm()
    } catch (err) {
      setError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (booking) => {
    setSelectedDate(booking.date)
    setForm({
      id: booking.id,
      customer_email: booking.customer_email,
      customer_name: booking.customer_name,
      date: booking.date,
      time_slot: booking.time_slot,
      vehicle_model: booking.vehicle_model,
      status: booking.status,
    })
    setNotice('')
    setError('')
  }

  const removeBooking = async (booking) => {
    if (!window.confirm(`Delete booking for ${booking.customer_email} at ${booking.slot_label}?`)) return
    setSaving(true)
    setError('')
    try {
      await deleteAdminBooking(booking.id)
      setNotice('Booking deleted.')
      await Promise.all([loadBookings(), loadSlots(selectedDate)])
      if (form.id === booking.id) resetForm()
    } catch (err) {
      setError(err.message || 'Delete failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-page">
      <header className="admin-header">
        <div>
          <h1>Admin Dashboard</h1>
          <p>{user?.full_name || 'Admin'} · booking control</p>
        </div>
        <button type="button" className="header-btn header-btn--ghost" onClick={logout}>
          Sign out
        </button>
      </header>

      <main className="admin-main">
        {error && <p className="form-error">{error}</p>}
        {notice && <p className="form-info">{notice}</p>}

        {/* Dashboard Statistics Header */}
        <section className="admin-stats-grid">
          <div className="admin-stat-card">
            <div className="admin-stat-card-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <div className="admin-stat-card-info">
              <h3>Total Users Booked</h3>
              <p className="admin-stat-card-number">{uniqueUsersCount}</p>
              <span className="admin-stat-card-sub">{totalBookings} total bookings</span>
            </div>
          </div>

          <div className="admin-stat-card">
            <div className="admin-stat-card-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            </div>
            <div className="admin-stat-card-info">
              <h3>Available Slots Capacity</h3>
              <p className="admin-stat-card-number">{totalSlotsCapacity}</p>
              <span className="admin-stat-card-sub">Showroom hours: {slotData?.showroom_hours || '10:00 am - 8:00 pm'}</span>
            </div>
          </div>

          <div className="admin-stat-card">
            <div className="admin-stat-card-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <div className="admin-stat-card-info">
              <h3>Remaining Slots</h3>
              <p className="admin-stat-card-number">{remainingSlots}</p>
              <span className="admin-stat-card-sub">For date: {selectedDate}</span>
            </div>
          </div>
        </section>

        <section className="admin-toolbar">
          <label>
            Date
            <select
              value={selectedDate}
              onChange={(e) => {
                setSelectedDate(e.target.value)
                setForm((current) => ({ ...current, date: e.target.value, time_slot: '' }))
              }}
            >
              {dates.map((date) => (
                <option key={date} value={date}>{date}</option>
              ))}
            </select>
          </label>
          {slotData && (
            <div className="admin-summary">
              <span>Now: {slotData.current_time}</span>
              <span>Hours: {slotData.showroom_hours}</span>
              <span>Available: {slotData.available_count}</span>
              <span>Taken: {slotData.taken_count}</span>
            </div>
          )}
        </section>

        <section className="admin-grid">
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>{isEditing ? 'Edit booking' : 'Create booking'}</h2>
              {isEditing && (
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  New
                </button>
              )}
            </div>
            <form className="admin-form" onSubmit={handleSubmit}>
              <label>
                Customer email
                <input
                  type="email"
                  value={form.customer_email}
                  disabled={isEditing}
                  onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
                  required={!isEditing}
                />
              </label>
              <label>
                Customer name
                <input
                  type="text"
                  value={form.customer_name}
                  disabled={isEditing}
                  onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                />
              </label>
              <label>
                Vehicle model
                <input
                  type="text"
                  value={form.vehicle_model}
                  onChange={(e) => setForm({ ...form, vehicle_model: e.target.value })}
                />
              </label>
              <label>
                Date
                <select
                  value={form.date}
                  onChange={(e) => {
                    setForm({ ...form, date: e.target.value, time_slot: '' })
                    setSelectedDate(e.target.value)
                  }}
                  required
                >
                  {dates.map((date) => (
                    <option key={date} value={date}>{date}</option>
                  ))}
                </select>
              </label>
              <label>
                Time slot
                <select
                  value={form.time_slot}
                  onChange={(e) => setForm({ ...form, time_slot: e.target.value })}
                  required
                >
                  <option value="">Select a slot</option>
                  {availableSlotOptions.map((slot) => (
                    <option key={slot.time} value={slot.time}>
                      {slot.label}{slot.available ? '' : ' (current booking)'}
                    </option>
                  ))}
                </select>
              </label>
              {isEditing && (
                <label>
                  Status
                  <select
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                  >
                    <option value="confirmed">Confirmed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </label>
              )}
              <button type="submit" className="btn-primary" disabled={saving || !form.time_slot}>
                {saving ? 'Saving...' : isEditing ? 'Update booking' : 'Create booking'}
              </button>
            </form>
          </div>

          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>Slots for {selectedDate}</h2>
            </div>
            <div className="admin-slot-grid">
              {(slotData?.slots || []).map((slot) => (
                <button
                  type="button"
                  key={slot.time}
                  className={`admin-slot ${slot.available ? 'admin-slot--available' : 'admin-slot--taken'}`}
                  onClick={() => {
                    if (slot.available) {
                      setForm((current) => ({ ...current, date: selectedDate, time_slot: slot.time }))
                    } else if (slot.booking?.id) {
                      const booking = bookings.find((item) => item.id === slot.booking.id)
                      if (booking) startEdit(booking)
                    }
                  }}
                >
                  <strong>{slot.label}</strong>
                  <span>{slot.available ? 'Available' : 'Taken'}</span>
                  {slot.booking && (
                    <small>{slot.booking.customer_name || slot.booking.customer_email}</small>
                  )}
                </button>
              ))}
              {!slotData?.slots?.length && <p className="panel-muted">No remaining slots for this date.</p>}
            </div>
          </div>
        </section>

        <section className="admin-panel admin-bookings-panel">
          <div className="admin-panel-header">
            <h2>All bookings</h2>
            <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
              Refresh
            </button>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Email</th>
                  <th>Date</th>
                  <th>Slot</th>
                  <th>Vehicle</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {bookings.map((booking) => (
                  <tr key={booking.id}>
                    <td>{booking.customer_name || '-'}</td>
                    <td>{booking.customer_email}</td>
                    <td>{booking.date}</td>
                    <td>{booking.slot_label}</td>
                    <td>{booking.vehicle_model}</td>
                    <td>{booking.status}</td>
                    <td className="admin-table-actions">
                      <button type="button" className="btn-secondary" onClick={() => startEdit(booking)}>
                        Edit
                      </button>
                      <button type="button" className="btn-danger" onClick={() => removeBooking(booking)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {!bookings.length && (
                  <tr>
                    <td colSpan="7">No bookings found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="admin-panel admin-bookings-panel">
          <div className="admin-panel-header">
            <h2>Chat monitor</h2>
            <button type="button" className="btn-secondary" onClick={loadChatLogs} disabled={logsLoading}>
              {logsLoading ? 'Loading...' : 'Refresh logs'}
            </button>
          </div>
          <p className="form-hint" style={{ padding: '0 16px 12px' }}>
            Track which user asked which query and what response was returned.
          </p>
          <div className="admin-table-wrap">
            <table className="admin-table admin-chat-logs-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Query</th>
                  <th>Response</th>
                  <th>Type</th>
                  <th>Found</th>
                </tr>
              </thead>
              <tbody>
                {chatLogs.map((log) => (
                  <tr key={log.id}>
                    <td className="admin-log-time">{new Date(log.created_at).toLocaleString()}</td>
                    <td>
                      <div>{log.user_name || (log.user_email === 'guest' ? 'Guest' : log.user_email)}</div>
                      <small className="admin-log-email">{log.user_email}</small>
                    </td>
                    <td className="admin-log-query">{log.query}</td>
                    <td className="admin-log-answer">{log.answer}</td>
                    <td>{log.response_type}</td>
                    <td>{log.found ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
                {!chatLogs.length && (
                  <tr>
                    <td colSpan="6">No chat interactions logged yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  )
}
