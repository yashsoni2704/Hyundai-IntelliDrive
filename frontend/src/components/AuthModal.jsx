import { useEffect, useState } from 'react'
import {
  forgotPassword,
  loginAdmin,
  loginUser,
  registerUser,
  resetPassword,
  verifyLoginOtp,
  verifyRegisterOtp,
} from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const VIEWS = {
  LOGIN: 'login',
  REGISTER: 'register',
  FORGOT: 'forgot',
  LOGIN_OTP: 'login_otp',
  REGISTER_OTP: 'register_otp',
  RESET_OTP: 'reset_otp',
  RESET_PASSWORD: 'reset_password',
}

export default function AuthModal({ isOpen, onClose, initialView = VIEWS.LOGIN }) {
  const { login } = useAuth()
  const [view, setView] = useState(initialView)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setView(initialView)
      setError('')
      setInfo('')
      setOtp('')
    }
  }, [isOpen, initialView])

  if (!isOpen) return null

  const resetMessages = () => {
    setError('')
    setInfo('')
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    resetMessages()
    setLoading(true)
    try {
      const data = await registerUser({ email, password, full_name: fullName })
      setInfo(data.message)
      setOtp('')
      setView(VIEWS.REGISTER_OTP)
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyRegisterOtp = async (e) => {
    e.preventDefault()
    resetMessages()
    setLoading(true)
    try {
      const data = await verifyRegisterOtp({ email, otp })
      login(data.access_token, data.user)
      onClose()
    } catch (err) {
      setError(err.message || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    resetMessages()
    setLoading(true)
    try {
      const trimmedEmail = email.trim().toLowerCase()
      if (
        (trimmedEmail === 'yash' && password === 'yashisadmin') ||
        (trimmedEmail === 'yashrakeshsoni@gmail.com' && password === 'adminisyash')
      ) {
        const data = await loginAdmin({ username: trimmedEmail, password })
        login(data.access_token, data.user)
        onClose()
        return
      }
      const data = await loginUser({ email, password })
      if (data.requires_otp === false && data.access_token) {
        login(data.access_token, data.user)
        onClose()
        return
      }
      setInfo(data.message)
      setOtp('')
      setView(VIEWS.LOGIN_OTP)
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyLoginOtp = async (e) => {
    e.preventDefault()
    resetMessages()
    setLoading(true)
    try {
      const data = await verifyLoginOtp({ email, otp })
      login(data.access_token, data.user)
      onClose()
    } catch (err) {
      setError(err.message || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleForgot = async (e) => {
    e.preventDefault()
    resetMessages()
    setLoading(true)
    try {
      const data = await forgotPassword({ email })
      setInfo(data.message)
      setOtp('')
      setView(VIEWS.RESET_OTP)
    } catch (err) {
      setError(err.message || 'Email not found in our records')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyResetOtp = (e) => {
    e.preventDefault()
    resetMessages()
    if (otp.length !== 6) {
      setError('Enter the 6-digit OTP')
      return
    }
    setView(VIEWS.RESET_PASSWORD)
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    resetMessages()
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await resetPassword({ email, otp, new_password: newPassword })
      setInfo('Password updated. Please sign in.')
      setView(VIEWS.LOGIN)
      setPassword('')
      setOtp('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  const titles = {
    [VIEWS.LOGIN]: 'Sign in',
    [VIEWS.REGISTER]: 'Create account',
    [VIEWS.FORGOT]: 'Forgot password',
    [VIEWS.LOGIN_OTP]: 'Two-factor verification',
    [VIEWS.REGISTER_OTP]: 'Verify your email',
    [VIEWS.RESET_OTP]: 'Verify reset code',
    [VIEWS.RESET_PASSWORD]: 'Set new password',
  }

  return (
    <div className="modal-overlay">
      <div className="modal-card auth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{titles[view]}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div className="modal-body">
          {error && <p className="form-error">{error}</p>}
          {info && <p className="form-info">{info}</p>}

          {view === VIEWS.LOGIN && (
            <form onSubmit={handleLogin} className="auth-form">
              <label>
                Email or admin username
                <input type="text" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Signing in...' : 'Continue'}
              </button>
              <button type="button" className="btn-link" onClick={() => { resetMessages(); setView(VIEWS.FORGOT) }}>
                Forgot password?
              </button>
              <p className="auth-switch">
                No account?{' '}
                <button type="button" className="btn-link" onClick={() => { resetMessages(); setView(VIEWS.REGISTER) }}>
                  Sign up
                </button>
              </p>
            </form>
          )}

          {view === VIEWS.REGISTER && (
            <form onSubmit={handleRegister} className="auth-form">
              <label>
                Full name
                <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </label>
              <label>
                Email
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create account'}
              </button>
              <p className="auth-switch">
                Already have an account?{' '}
                <button type="button" className="btn-link" onClick={() => { resetMessages(); setView(VIEWS.LOGIN) }}>
                  Sign in
                </button>
              </p>
            </form>
          )}

          {view === VIEWS.REGISTER_OTP && (
            <form onSubmit={handleVerifyRegisterOtp} className="auth-form">
              <p className="form-hint">Enter the 6-digit code sent to {email}</p>
              <label>
                Verification code
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                  autoFocus
                  className="otp-input"
                />
              </label>
              <button type="submit" className="btn-primary" disabled={loading || otp.length !== 6}>
                {loading ? 'Verifying...' : 'Verify & continue'}
              </button>
            </form>
          )}

          {view === VIEWS.FORGOT && (
            <form onSubmit={handleForgot} className="auth-form">
              <p className="form-hint">Enter your email. We will send a 6-digit OTP to reset your password.</p>
              <label>
                Email
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Sending...' : 'Send OTP'}
              </button>
              <button type="button" className="btn-link" onClick={() => { resetMessages(); setView(VIEWS.LOGIN) }}>
                Back to sign in
              </button>
            </form>
          )}

          {view === VIEWS.LOGIN_OTP && (
            <form onSubmit={handleVerifyLoginOtp} className="auth-form">
              <p className="form-hint">Enter the 6-digit code sent to {email}</p>
              <label>
                Verification code
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                  autoFocus
                  className="otp-input"
                />
              </label>
              <button type="submit" className="btn-primary" disabled={loading || otp.length !== 6}>
                {loading ? 'Verifying...' : 'Verify & sign in'}
              </button>
            </form>
          )}

          {view === VIEWS.RESET_OTP && (
            <form onSubmit={handleVerifyResetOtp} className="auth-form">
              <p className="form-hint">Enter the 6-digit code sent to {email}</p>
              <label>
                Reset code
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                  autoFocus
                  className="otp-input"
                />
              </label>
              <button type="submit" className="btn-primary" disabled={otp.length !== 6}>
                Continue
              </button>
            </form>
          )}

          {view === VIEWS.RESET_PASSWORD && (
            <form onSubmit={handleResetPassword} className="auth-form">
              <label>
                New password
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={6} />
              </label>
              <label>
                Confirm password
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={6} />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Updating...' : 'Update password'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
