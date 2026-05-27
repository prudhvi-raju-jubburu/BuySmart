import React, { useEffect, useState } from 'react';
import './AuthModal.css';
import { loginUser, registerUser, getMe, logoutUser } from '../services/api';

const AuthModal = ({ open, mode, onClose, onAuthChange }) => {
  const [tab, setTab] = useState(mode || 'login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [me, setMe] = useState(null);

  useEffect(() => {
    setTab(mode || 'login');
  }, [mode]);

  useEffect(() => {
    const token = localStorage.getItem('buysmart_token');
    if (!open || !token) {
      setMe(null);
      return;
    }
    (async () => {
      try {
        const data = await getMe();
        setMe(data.data?.user || data.user);
      } catch (_e) {
        setMe(null);
      }
    })();
  }, [open]);

  if (!open) return null;

  const doLogin = async () => {
    setBusy(true);
    try {
      const data = await loginUser({ email, password });
      // Store JWT access and refresh tokens
      const accessToken = data.data?.access_token || data.token;
      const refreshToken = data.data?.refresh_token;
      localStorage.setItem('buysmart_token', accessToken);
      if (refreshToken) {
        localStorage.setItem('buysmart_refresh_token', refreshToken);
      }
      const user = data.data?.user || data.user;
      onAuthChange?.(user);
      setPassword('');
      onClose?.();
    } catch (e) {
      alert(e?.response?.data?.message || e?.response?.data?.error || 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  const doRegister = async () => {
    setBusy(true);
    try {
      await registerUser({ name, email, password });
      await doLogin();
    } catch (e) {
      alert(e?.response?.data?.message || e?.response?.data?.error || 'Register failed');
      setBusy(false);
    }
  };

  const doLogout = async () => {
    setBusy(true);
    try {
      await logoutUser();
    } catch (_e) {
      // ignore
    } finally {
      localStorage.removeItem('buysmart_token');
      localStorage.removeItem('buysmart_refresh_token');
      onAuthChange?.(null);
      setMe(null);
      setBusy(false);
      onClose?.();
    }
  };

  return (
    <div className="authmodal-backdrop" onClick={onClose}>
      <div className="authmodal" onClick={(e) => e.stopPropagation()}>
        <div className="authmodal-header">
          <div className="authmodal-title">Account</div>
          <button className="authmodal-close" onClick={onClose}>✕</button>
        </div>

        {me ? (
          <div className="authmodal-body">
            <div className="authmodal-me">
              Logged in as <b>{me.name}</b><div className="muted">{me.email}</div>
            </div>
            <button className="authmodal-btn" onClick={doLogout} disabled={busy}>
              Logout
            </button>
          </div>
        ) : (
          <>
            <div className="authmodal-tabs">
              <button className={`tab ${tab === 'login' ? 'active' : ''}`} onClick={() => setTab('login')} disabled={busy}>
                Login
              </button>
              <button className={`tab ${tab === 'register' ? 'active' : ''}`} onClick={() => setTab('register')} disabled={busy}>
                Register
              </button>
            </div>

            <div className="authmodal-body">
              {tab === 'register' && (
                <input className="authmodal-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
              )}
              <input className="authmodal-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
              <input className="authmodal-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />

              <button
                className="authmodal-btn"
                onClick={tab === 'login' ? doLogin : doRegister}
                disabled={busy}
              >
                {busy ? 'Please wait...' : tab === 'login' ? 'Login' : 'Create Account'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthModal;





