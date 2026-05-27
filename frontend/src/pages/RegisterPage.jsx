import React, { useState, useCallback } from 'react';
import './auth.css';
import { registerUser } from '../services/api';

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

// ── Password Strength Logic ────────────────────────────────────────
const PW_RULES = [
  { key: 'len',     label: 'At least 8 characters',     test: p => p.length >= 8 },
  { key: 'upper',   label: 'One uppercase letter',       test: p => /[A-Z]/.test(p) },
  { key: 'lower',   label: 'One lowercase letter',       test: p => /[a-z]/.test(p) },
  { key: 'digit',   label: 'One number',                 test: p => /\d/.test(p) },
  { key: 'special', label: 'One special character',      test: p => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'`~/]/.test(p) },
];

const STRENGTH_LEVELS = [
  { label: 'Weak',      color: '#ef4444', pct: 20 },
  { label: 'Fair',      color: '#f97316', pct: 40 },
  { label: 'Good',      color: '#eab308', pct: 60 },
  { label: 'Strong',    color: '#22c55e', pct: 80 },
  { label: 'Very Strong', color: '#16a34a', pct: 100 },
];

function getStrength(password) {
  if (!password) return null;
  const passed = PW_RULES.filter(r => r.test(password)).length;
  return STRENGTH_LEVELS[Math.min(passed - 1, 4)] || STRENGTH_LEVELS[0];
}

// ── Field Validators ──────────────────────────────────────────────
function validateField(name, value, fields = {}) {
  switch (name) {
    case 'name': {
      const n = value.trim();
      if (!n) return 'Full name is required';
      if (n.length < 3) return 'Name must be at least 3 characters';
      if (n.length > 50) return 'Name must be 50 characters or fewer';
      if (n.replace(/\s/g, '').match(/^\d+$/)) return 'Name cannot be purely numeric';
      return '';
    }
    case 'email': {
      const emailVal = value.trim();
      const phoneVal = (fields.phone || '').trim();
      if (!emailVal && !phoneVal) return 'Email address or phone number is required';
      if (emailVal && !EMAIL_RE.test(emailVal)) return 'Enter a valid email (e.g. you@example.com)';
      return '';
    }
    case 'phone': {
      const phoneVal = value.trim();
      const emailVal = (fields.email || '').trim();
      if (!phoneVal && !emailVal) return 'Email address or phone number is required';
      if (phoneVal && !PHONE_RE.test(phoneVal)) return 'Enter a valid Indian mobile number (e.g. 9876543210)';
      return '';
    }
    case 'password': {
      if (!value) return 'Password is required';
      const failing = PW_RULES.filter(r => !r.test(value));
      if (failing.length > 0) return `Missing: ${failing.map(r => r.label.toLowerCase()).join(', ')}`;
      return '';
    }
    case 'confirm': {
      if (!value) return 'Please confirm your password';
      if (value !== fields.password) return 'Passwords do not match';
      return '';
    }
    default: return '';
  }
}

// ── Component ─────────────────────────────────────────────────────
const RegisterPage = ({ onAuthChange, onNavigate, onShowToast }) => {
  const [fields, setFields] = useState({ name: '', email: '', phone: '', password: '', confirm: '' });
  const [touched, setTouched] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const strength = getStrength(fields.password);
  const pwRuleResults = PW_RULES.map(r => ({ ...r, ok: r.test(fields.password) }));

  const getErr = useCallback((name) => {
    if (!touched[name] && !error) return '';
    return validateField(name, fields[name], fields);
  }, [touched, fields, error]);

  const handleChange = (name, value) => {
    setFields(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleBlur = (name) => setTouched(prev => ({ ...prev, [name]: true }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    // Touch all fields to show errors
    const allTouched = Object.fromEntries(Object.keys(fields).map(k => [k, true]));
    setTouched(allTouched);

    const errs = Object.keys(fields).map(k => validateField(k, fields[k], fields)).filter(Boolean);
    if (errs.length > 0) return;

    setBusy(true);
    try {
      const data = await registerUser({
        name: fields.name.trim(),
        email: fields.email.trim().toLowerCase(),
        phone_number: fields.phone.trim(),
        password: fields.password,
      });

      // Auto-login: store tokens from registration response
      const accessToken = data.data?.access_token;
      const refreshToken = data.data?.refresh_token;
      if (accessToken) {
        localStorage.setItem('buysmart_token', accessToken);
        if (refreshToken) localStorage.setItem('buysmart_refresh_token', refreshToken);
      }

      const user = data.data?.user;
      onAuthChange?.(user);
      onShowToast?.('🎉 Account created successfully! Welcome to BuySmart.', 'success');
      onNavigate?.('search');
    } catch (err) {
      const msg = err?.response?.data?.message || 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  // Confirm password match state (only show if user has typed something)
  const confirmMatch = fields.confirm.length > 0
    ? (fields.confirm === fields.password ? 'match' : 'mismatch')
    : null;

  const inputClass = (name) => {
    const err = getErr(name);
    const ok = touched[name] && !err && fields[name];
    return `auth-input${name === 'password' || name === 'confirm' ? ' has-toggle' : ''}${err ? ' input-error' : ok ? ' input-success' : ''}`;
  };

  return (
    <div className="auth-page">
      {/* Branding panel */}
      <div className="auth-brand">
        <div className="auth-brand-content">
          <div className="auth-brand-logo">Buy<span>Smart</span></div>
          <div className="auth-brand-tagline">Join millions of smart shoppers</div>
          <div className="auth-brand-sub">
            Create your free account and start saving on every purchase today.
          </div>
          <div className="auth-brand-features">
            {[
              { icon: '⚡', text: 'Instant price comparison' },
              { icon: '🤖', text: 'AI-powered search' },
              { icon: '🔔', text: 'Price drop notifications' },
              { icon: '🛍️', text: 'Wishlist across platforms' },
            ].map((f, i) => (
              <div className="auth-brand-feature" key={i}>
                <div className="auth-brand-feature-icon">{f.icon}</div>
                {f.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h1 className="auth-form-title">Create Your BuySmart Account</h1>
          <p className="auth-form-subtitle">Free forever. No credit card required.</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {error && (
              <div className="auth-error-banner" role="alert">
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: '1px' }}>
                  <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
                </svg>
                {error}
              </div>
            )}

            {/* Full Name */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-name">Full Name</label>
              <input
                id="reg-name"
                className={inputClass('name')}
                type="text"
                autoComplete="name"
                placeholder="Priya Sharma"
                value={fields.name}
                onChange={e => handleChange('name', e.target.value)}
                onBlur={() => handleBlur('name')}
                disabled={busy}
              />
              {getErr('name') && <span className="auth-field-msg error">⚠ {getErr('name')}</span>}
            </div>

            {/* Email */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-email">Email Address</label>
              <input
                id="reg-email"
                className={inputClass('email')}
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={fields.email}
                onChange={e => handleChange('email', e.target.value)}
                onBlur={() => handleBlur('email')}
                disabled={busy}
              />
              {getErr('email') && <span className="auth-field-msg error">⚠ {getErr('email')}</span>}
            </div>

            {/* Phone */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-phone">Phone Number</label>
              <input
                id="reg-phone"
                className={inputClass('phone')}
                type="tel"
                autoComplete="tel"
                placeholder="9876543210 or +919876543210"
                value={fields.phone}
                onChange={e => handleChange('phone', e.target.value)}
                onBlur={() => handleBlur('phone')}
                disabled={busy}
                maxLength={13}
              />
              {getErr('phone') && <span className="auth-field-msg error">⚠ {getErr('phone')}</span>}
            </div>

            {/* Password + strength meter */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-password">Password</label>
              <div className="auth-input-wrap">
                <input
                  id="reg-password"
                  className={inputClass('password')}
                  type={showPw ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Create a strong password"
                  value={fields.password}
                  onChange={e => handleChange('password', e.target.value)}
                  onBlur={() => handleBlur('password')}
                  disabled={busy}
                />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(s => !s)} tabIndex={-1} aria-label="Toggle password">
                  <EyeIcon open={showPw} />
                </button>
              </div>

              {/* Strength meter (shown when user starts typing) */}
              {fields.password.length > 0 && strength && (
                <div className="pw-strength-wrap">
                  <div className="pw-strength-bar-track">
                    <div className="pw-strength-bar-fill" style={{ width: `${strength.pct}%`, backgroundColor: strength.color }} />
                  </div>
                  <div className="pw-strength-label" style={{ color: strength.color }}>{strength.label}</div>
                  <div className="pw-rules">
                    {pwRuleResults.map(r => (
                      <div key={r.key} className={`pw-rule ${r.ok ? 'rule-ok' : ''}`}>
                        <span className="rule-dot" />
                        {r.label}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-confirm">Confirm Password</label>
              <div className="auth-input-wrap">
                <input
                  id="reg-confirm"
                  className={`auth-input has-toggle${confirmMatch === 'mismatch' ? ' input-error' : confirmMatch === 'match' ? ' input-success' : ''}`}
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Repeat your password"
                  value={fields.confirm}
                  onChange={e => handleChange('confirm', e.target.value)}
                  onBlur={() => handleBlur('confirm')}
                  disabled={busy}
                />
                <button type="button" className="pw-toggle" onClick={() => setShowConfirm(s => !s)} tabIndex={-1} aria-label="Toggle confirm password">
                  <EyeIcon open={showConfirm} />
                </button>
              </div>
              {confirmMatch === 'match' && (
                <span className="confirm-pw-match match">✓ Passwords match</span>
              )}
              {confirmMatch === 'mismatch' && (
                <span className="confirm-pw-match mismatch">✗ Passwords do not match</span>
              )}
            </div>

            <button type="submit" className="auth-submit-btn" disabled={busy} id="register-submit-btn">
              {busy ? <><span className="btn-spinner" /> Creating account...</> : 'Create Account'}
            </button>
          </form>

          <div className="auth-switch">
            Already have an account?{' '}
            <button className="auth-switch-btn" onClick={() => onNavigate?.('login')} disabled={busy}>
              Sign in →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
