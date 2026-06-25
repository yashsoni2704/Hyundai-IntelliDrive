import { useCallback, useEffect, useState } from 'react'
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

function OtpField({ otp, setOtp, label = 'Verification code' }) {
  return (
    <label>
      {label}
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        value={otp}
        onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
        maxLength={6}
        required
        autoFocus
        className="otp-input"
        placeholder="000000"
      />
      <span className="form-hint">Paste the 6-digit code from your email.</span>
    </label>
  )
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

  const resetForm = useCallback(() => {
    setEmail('')
    setPassword('')
    setFullName('')
    setOtp('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
    setInfo('')
  }, [])

  useEffect(() => {
    if (isOpen) {
      setView(initialView)
      resetForm()
    }
  }, [isOpen, initialView, resetForm])

  if (!isOpen) return null

  const resetMessages = () => {
    setError('')
    setInfo('')
  }

  const goToLogin = () => {
    resetMessages()
    setPassword('')
    setOtp('')
    setView(VIEWS.LOGIN)
  }

  const goToRegister = (keepEmail = false, keepMessages = false) => {
    if (!keepMessages) resetMessages()
    if (!keepEmail) setEmail('')
    setPassword('')
    setFullName('')
    setOtp('')
    setView(VIEWS.REGISTER)
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
      const msg = err.message || 'Registration failed'
      if (msg.toLowerCase().includes('already registered')) {
        setError('This email is already registered. Please sign in instead.')
        setPassword('')
        setView(VIEWS.LOGIN)
      } else {
        setError(msg)
      }
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
      setError(err.message || 'Invalid or expired code. Check your email and try again.')
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
      setInfo(data.message || 'Enter the verification code sent to your email.')
      setOtp('')
      setView(VIEWS.LOGIN_OTP)
    } catch (err) {
      setPassword('')
      if (err.status === 404) {
        setError(err.message || 'No account found. Please create an account to use the chatbot.')
        setInfo('Fill in your details below to sign up.')
        goToRegister(true, true)
      } else if (err.status === 401) {
        setError(err.message || 'Incorrect password.')
      } else if (err.status === 503) {
        setError('Could not send verification email. Try again in a moment.')
      } else {
        setError(err.message || 'Sign in failed. Check your details and try again.')
      }
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
      setError(err.message || 'Invalid or expired code. Check your email and try again.')
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
      if (err.status === 404) {
        setError(err.message || 'No account found with this email. Please create an account first.')
        setInfo('You can sign up below with the same email.')
        goToRegister(true, true)
      } else {
        setError(err.message || 'Could not send reset code. Try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyResetOtp = (e) => {
    e.preventDefault()
    resetMessages()
    if (otp.length !== 6) {
      setError('Enter the full 6-digit code from your email.')
      return
    }
    setView(VIEWS.RESET_PASSWORD)
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    resetMessages()
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await resetPassword({ email, otp, new_password: newPassword })
      setInfo('Password updated. Sign in with your new password.')
      setError('')
      setPassword('')
      setOtp('')
      setNewPassword('')
      setConfirmPassword('')
      setView(VIEWS.LOGIN)
    } catch (err) {
      setError(err.message || 'Failed to reset password. Request a new code and try again.')
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

  const preventAutofill = {
    autoComplete: 'off',
    autoCorrect: 'off',
    autoCapitalize: 'off',
    spellCheck: false,
    readOnly: true,
    onFocus: (e) => {
      e.target.readOnly = false
    },
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
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
          {error && <p className="form-error" role="alert">{error}</p>}
          {info && <p className={`form-info${error ? ' form-info--after-error' : ''}`}>{info}</p>}

          {view === VIEWS.LOGIN && (
            <form onSubmit={handleLogin} className="auth-form" autoComplete="off">
              <label>
                <span className="field-label">Email</span>
                <input
                  type="email"
                  name="hyundai_login_email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  {...preventAutofill}
                />
              </label>
              <label>
                <span className="field-label">Password</span>
                <input
                  type="password"
                  name="hyundai_login_password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  readOnly
                  onFocus={(e) => {
                    e.target.readOnly = false
                  }}
                />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Signing in...' : 'Continue'}
              </button>
              <button type="button" className="btn-link" onClick={() => { resetMessages(); setView(VIEWS.FORGOT) }}>
                Forgot password?
              </button>
              <p className="auth-switch">
                No account?{' '}
                <button type="button" className="btn-link inline" onClick={() => goToRegister(false)}>
                  Sign up
                </button>
              </p>
            </form>
          )}

          {view === VIEWS.REGISTER && (
            <form onSubmit={handleRegister} className="auth-form" autoComplete="off">
              <label>
                <span className="field-label">Full name</span>
                <input
                  type="text"
                  name="hyundai_register_name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  {...preventAutofill}
                />
              </label>
              <label>
                <span className="field-label">Email</span>
                <input
                  type="email"
                  name="hyundai_register_email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  {...preventAutofill}
                />
              </label>
              <label>
                <span className="field-label">Password</span>
                <input
                  type="password"
                  name="hyundai_register_password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete="new-password"
                  readOnly
                  onFocus={(e) => {
                    e.target.readOnly = false
                  }}
                />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create account'}
              </button>
              <p className="auth-switch">
                Already have an account?{' '}
                <button type="button" className="btn-link inline" onClick={goToLogin}>
                  Sign in
                </button>
              </p>
            </form>
          )}

          {view === VIEWS.REGISTER_OTP && (
            <form onSubmit={handleVerifyRegisterOtp} className="auth-form" autoComplete="off">
              <p className="form-hint">We sent a 6-digit code to <strong>{email}</strong></p>
              <OtpField otp={otp} setOtp={setOtp} label="Verification code" />
              <button type="submit" className="btn-primary" disabled={loading || otp.length !== 6}>
                {loading ? 'Verifying...' : 'Verify & continue'}
              </button>
            </form>
          )}

          {view === VIEWS.FORGOT && (
            <form onSubmit={handleForgot} className="auth-form" autoComplete="off">
              <p className="form-hint">Enter your account email. We will send a reset code.</p>
              <label>
                <span className="field-label">Email</span>
                <input
                  type="email"
                  name="hyundai_forgot_email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  {...preventAutofill}
                />
              </label>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Sending...' : 'Send OTP'}
              </button>
              <button type="button" className="btn-link" onClick={goToLogin}>
                Back to sign in
              </button>
            </form>
          )}

          {view === VIEWS.LOGIN_OTP && (
            <form onSubmit={handleVerifyLoginOtp} className="auth-form" autoComplete="off">
              <p className="form-hint">We sent a 6-digit code to <strong>{email}</strong></p>
              <OtpField otp={otp} setOtp={setOtp} label="Verification code" />
              <button type="submit" className="btn-primary" disabled={loading || otp.length !== 6}>
                {loading ? 'Verifying...' : 'Verify & sign in'}
              </button>
            </form>
          )}

          {view === VIEWS.RESET_OTP && (
            <form onSubmit={handleVerifyResetOtp} className="auth-form" autoComplete="off">
              <p className="form-hint">We sent a reset code to <strong>{email}</strong></p>
              <OtpField otp={otp} setOtp={setOtp} label="Reset code" />
              <button type="submit" className="btn-primary" disabled={otp.length !== 6}>
                Continue
              </button>
            </form>
          )}

          {view === VIEWS.RESET_PASSWORD && (
            <form onSubmit={handleResetPassword} className="auth-form" autoComplete="off">
              <label>
                <span className="field-label">New password</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete="new-password"
                />
              </label>
              <label>
                <span className="field-label">Confirm password</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete="new-password"
                />
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
