import React, { useState, useCallback } from 'react';
import './auth.css';
import { loginUser } from '../services/api';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^(\+91)?[6-9]\d{9}$/;

const EyeIcon = ({ open }) => open ? (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
) : (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
  </svg>
);

const LoginPage = ({ onAuthChange, onNavigate, onShowToast }) => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const validateField = useCallback((name, value) => {
    if (name === 'identifier') {
      if (!value.trim()) return 'Email or phone number is required';
      const v = value.trim();
      if (v.includes('@') && !EMAIL_RE.test(v)) return 'Enter a valid email address';
      if (!v.includes('@') && v.length > 0 && !PHONE_RE.test(v)) return 'Enter a valid Indian phone number';
    }
    if (name === 'password') {
      if (!value) return 'Password is required';
    }
    return '';
  }, []);

  const handleBlur = (name, value) => {
    const err = validateField(name, value);
    setFieldErrors(prev => ({ ...prev, [name]: err }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const idErr = validateField('identifier', identifier);
    const pwErr = validateField('password', password);
    setFieldErrors({ identifier: idErr, password: pwErr });
    if (idErr || pwErr) return;

    setBusy(true);
    try {
      const data = await loginUser({ identifier: identifier.trim(), password });
      const accessToken = data.data?.access_token;
      const refreshToken = data.data?.refresh_token;

      if (remember) {
        localStorage.setItem('buysmart_token', accessToken);
        if (refreshToken) localStorage.setItem('buysmart_refresh_token', refreshToken);
      } else {
        sessionStorage.setItem('buysmart_token', accessToken);
        if (refreshToken) sessionStorage.setItem('buysmart_refresh_token', refreshToken);
        // Keep localStorage clean for non-remember sessions
        localStorage.removeItem('buysmart_token');
        localStorage.removeItem('buysmart_refresh_token');
      }

      const user = data.data?.user;
      onAuthChange?.(user);
      onShowToast?.(`Welcome back, ${user?.name?.split(' ')[0] || 'there'}! 👋`, 'success');
      onNavigate?.('search');
    } catch (err) {
      const msg = err?.response?.data?.message || 'Login failed. Please try again.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleForgotPassword = () => {
    onShowToast?.('Password reset coming soon — check back later.', 'info');
  };

  return (
    <div className="auth-page">
      {/* Left branding panel */}
      <div className="auth-brand">
        <div className="auth-brand-content">
          <div className="auth-brand-logo">Buy<span>Smart</span></div>
          <div className="auth-brand-tagline">India's Smartest Shopping Companion</div>
          <div className="auth-brand-sub">
            Compare prices across Amazon, Flipkart, Myntra, and more — all in one place.
          </div>
          <div className="auth-brand-features">
            {[
              { icon: '🔍', text: 'AI-powered product search' },
              { icon: '💰', text: 'Real-time price comparison' },
              { icon: '📊', text: 'Price drop alerts' },
              { icon: '❤️', text: 'Personalised recommendations' },
            ].map((f, i) => (
              <div className="auth-brand-feature" key={i}>
                <div className="auth-brand-feature-icon">{f.icon}</div>
                {f.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h1 className="auth-form-title">Welcome Back</h1>
          <p className="auth-form-subtitle">Sign in to continue to BuySmart</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {/* Error banner */}
            {error && (
              <div className="auth-error-banner" role="alert">
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: '1px' }}>
                  <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
                </svg>
                {error}
              </div>
            )}

            {/* Identifier field */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="login-identifier">Email or Phone Number</label>
              <div className="auth-input-wrap">
                <input
                  id="login-identifier"
                  className={`auth-input${fieldErrors.identifier ? ' input-error' : ''}`}
                  type="text"
                  autoComplete="username"
                  placeholder="you@email.com or 9876543210"
                  value={identifier}
                  onChange={e => { setIdentifier(e.target.value); setError(''); }}
                  onBlur={e => handleBlur('identifier', e.target.value)}
                  disabled={busy}
                />
              </div>
              {fieldErrors.identifier && (
                <span className="auth-field-msg error">⚠ {fieldErrors.identifier}</span>
              )}
            </div>

            {/* Password field */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="login-password">Password</label>
              <div className="auth-input-wrap">
                <input
                  id="login-password"
                  className={`auth-input has-toggle${fieldErrors.password ? ' input-error' : ''}`}
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError(''); }}
                  onBlur={e => handleBlur('password', e.target.value)}
                  disabled={busy}
                />
                <button
                  type="button"
                  className="pw-toggle"
                  onClick={() => setShowPw(s => !s)}
                  tabIndex={-1}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  <EyeIcon open={showPw} />
                </button>
              </div>
              {fieldErrors.password && (
                <span className="auth-field-msg error">⚠ {fieldErrors.password}</span>
              )}
            </div>

            {/* Remember Me + Forgot Password */}
            <div className="auth-extras">
              <label className="auth-remember">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={e => setRemember(e.target.checked)}
                  disabled={busy}
                />
                Remember me
              </label>
              <button type="button" className="auth-forgot" onClick={handleForgotPassword}>
                Forgot Password?
              </button>
            </div>

            {/* Submit */}
            <button type="submit" className="auth-submit-btn" disabled={busy} id="login-submit-btn">
              {busy ? <><span className="btn-spinner" /> Signing in...</> : 'Sign In'}
            </button>
          </form>

          {/* Switch to Register */}
          <div className="auth-switch">
            Don't have an account?{' '}
            <button className="auth-switch-btn" onClick={() => onNavigate?.('register')} disabled={busy}>
              Create account →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
