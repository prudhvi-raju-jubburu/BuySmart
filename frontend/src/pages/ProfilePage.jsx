import React, { useState, useEffect, useCallback } from 'react';
import './ProfilePage.css';
import { 
  updateProfile, 
  changePassword, 
  getWishlist, 
  getSearchHistory, 
  logoutUser 
} from '../services/api';
import { SkeletonProfile } from '../components/SkeletonCard';

// ── Helpers ────────────────────────────────────────────────────────
const PHONE_RE = /^(\+91)?[6-9]\d{9}$/;

function getInitials(name = '') {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() || '')
    .join('');
}

function formatMemberSince(dateStr) {
  if (!dateStr) return 'Unknown';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
}

// ── Password Strength ──────────────────────────────────────────────
const PW_RULES = [
  { key: 'len',     label: 'At least 8 characters',     test: p => p.length >= 8 },
  { key: 'upper',   label: 'One uppercase letter',       test: p => /[A-Z]/.test(p) },
  { key: 'lower',   label: 'One lowercase letter',       test: p => /[a-z]/.test(p) },
  { key: 'digit',   label: 'One number',                 test: p => /\d/.test(p) },
  { key: 'special', label: 'One special character',      test: p => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'`~/]/.test(p) },
];
const STRENGTH_LEVELS = [
  { label: 'Weak',       color: '#ef4444', pct: 20 },
  { label: 'Fair',       color: '#f97316', pct: 40 },
  { label: 'Good',       color: '#eab308', pct: 60 },
  { label: 'Strong',     color: '#22c55e', pct: 80 },
  { label: 'Very Strong',color: '#16a34a', pct: 100 },
];
function getStrength(pw) {
  if (!pw) return null;
  const passed = PW_RULES.filter(r => r.test(pw)).length;
  return STRENGTH_LEVELS[Math.min(passed - 1, 4)];
}

const EyeIcon = ({ open }) => open ? (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
) : (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59" />
  </svg>
);

// ── Main Component ─────────────────────────────────────────────────
const ProfilePage = ({ user, onProfileUpdate, onNavigate, onShowToast }) => {
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPageLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  // Stats
  const [stats, setStats] = useState({ searches: 0, wishlist: 0 });

  // Edit Profile
  const [editName, setEditName] = useState(user?.name || '');
  const [editPhone, setEditPhone] = useState(user?.phone_number || '');
  const [editBusy, setEditBusy] = useState(false);
  const [editErrors, setEditErrors] = useState({});

  // Change Password
  const [pwFields, setPwFields] = useState({ current: '', newPw: '', confirm: '' });
  const [pwShow, setPwShow] = useState({ current: false, newPw: false, confirm: false });
  const [pwBusy, setPwBusy] = useState(false);
  const [pwErrors, setPwErrors] = useState({});

  // Load stats
  const fetchDashboardData = useCallback(async () => {
    try {
      const [wl, sh] = await Promise.allSettled([
        getWishlist(),
        getSearchHistory({ limit: 1000 })
      ]);

      const shVal = sh.status === 'fulfilled' ? (sh.value?.total || sh.value?.items?.length || 0) : 0;
      const wlVal = wl.status === 'fulfilled' ? (wl.value?.items?.length || 0) : 0;
      setStats({
        wishlist: wlVal,
        searches: shVal,
      });
    } catch (err) {
      console.error('Failed to load dashboard stats.');
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchDashboardData();
    }
  }, [user, fetchDashboardData]);

  // ── Edit Profile submit ──────────────────────────────────────────
  const handleEditSave = async (e) => {
    e.preventDefault();
    const errs = {};
    const n = editName.trim();
    const p = editPhone.trim();

    if (!n) { errs.name = 'Name is required'; }
    else if (n.length < 3) { errs.name = 'Name must be at least 3 characters'; }
    else if (n.length > 50) { errs.name = 'Name must be 50 characters or fewer'; }
    else if (n.replace(/\s/g, '').match(/^\d+$/)) { errs.name = 'Name cannot be purely numeric'; }

    if (p && !PHONE_RE.test(p)) { errs.phone = 'Enter a valid Indian mobile number'; }

    setEditErrors(errs);
    if (Object.keys(errs).length) return;

    setEditBusy(true);
    try {
      const data = await updateProfile({ name: n, phone_number: p || undefined });
      onProfileUpdate?.(data.data.user);
      onShowToast?.('✓ Profile updated successfully.', 'success');
    } catch (err) {
      const msg = err?.response?.data?.message || 'Update failed';
      setEditErrors({ form: msg });
    } finally {
      setEditBusy(false);
    }
  };

  // ── Change Password submit ───────────────────────────────────────
  const handlePwChange = async (e) => {
    e.preventDefault();
    const errs = {};

    if (!pwFields.current) errs.current = 'Current password is required';
    if (!pwFields.newPw) {
      errs.newPw = 'New password is required';
    } else {
      const failing = PW_RULES.filter(r => !r.test(pwFields.newPw));
      if (failing.length) errs.newPw = `Missing: ${failing.map(r => r.label.toLowerCase()).join(', ')}`;
    }
    if (!pwFields.confirm) { errs.confirm = 'Please confirm your new password'; }
    else if (pwFields.confirm !== pwFields.newPw) { errs.confirm = 'Passwords do not match'; }
    if (pwFields.current && pwFields.newPw && pwFields.current === pwFields.newPw) {
      errs.newPw = 'New password must be different from current password';
    }

    setPwErrors(errs);
    if (Object.keys(errs).length) return;

    setPwBusy(true);
    try {
      await changePassword({ current_password: pwFields.current, new_password: pwFields.newPw });
      setPwFields({ current: '', newPw: '', confirm: '' });
      setPwErrors({});
      onShowToast?.('✓ Password changed successfully.', 'success');
    } catch (err) {
      const msg = err?.response?.data?.message || 'Failed to change password';
      setPwErrors({ form: msg });
    } finally {
      setPwBusy(false);
    }
  };

  // ── Logout ───────────────────────────────────────────────────────
  const handleLogout = async () => {
    try { await logoutUser(); } catch (_) {}
    localStorage.removeItem('buysmart_token');
    localStorage.removeItem('buysmart_refresh_token');
    onProfileUpdate?.(null);
    onNavigate?.('home');
  };

  const newPwStrength = getStrength(pwFields.newPw);
  const isAdmin = user?.is_admin || user?.role === 'admin';

  return (
    <div className="profile-page">
      <div className="profile-inner">
        
        {/* Back button */}
        <button className="profile-back-btn" onClick={() => onNavigate?.('search')}>
          ← Back to Search
        </button>

        {/* Standardized Page Header */}
        <div className="page-header-card">
          <h2 className="page-title">Account Settings</h2>
          <p className="page-subtitle">Manage your personal information and security.</p>
        </div>

        {pageLoading ? (
          <SkeletonProfile />
        ) : (
          <>
            {/* 1. Profile Header */}
            <div className="profile-card profile-header-centered">
          <div className="profile-avatar-large">{getInitials(user?.name)}</div>
          <h2 className="profile-name-large">{user?.name || 'Unknown User'}</h2>
          
          <div className="profile-member-since">
            Member since {formatMemberSince(user?.created_at)}
          </div>
          
          {isAdmin && (
            <div className="profile-admin-badge" style={{ marginTop: '0.5rem' }}>
              ⭐ Administrator
            </div>
          )}

          <div className="profile-contact-info">
            <span className="contact-item">📧 {user?.email || 'Email not added'}</span>
            <span className="contact-item">📱 {user?.phone_number ? `+91 ${user.phone_number}` : 'Phone not added'}</span>
          </div>

          <button className="profile-edit-trigger-btn" onClick={() => {
            document.getElementById('edit-profile-section').scrollIntoView({ behavior: 'smooth' });
          }}>
            Edit Profile
          </button>

          {isAdmin && (
            <button className="profile-admin-panel-btn" onClick={() => onNavigate?.('admin-dashboard')} style={{ marginTop: '0.5rem' }}>
              🛡️ Go to Admin Panel
            </button>
          )}

          {/* Contact missing banners */}
          {(!user?.phone_number || !user?.email) && (
            <div className="profile-warnings" style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {!user?.phone_number && (
                <div className="phone-missing-banner">
                  ⚠️ Add a phone number to your profile for account security.
                </div>
              )}
              {!user?.email && (
                <div className="phone-missing-banner">
                  ⚠️ Add an email address to receive price drops and alerts.
                </div>
              )}
            </div>
          )}
        </div>

        {/* 2. Statistics Row */}
        <div className="profile-kpi-grid">
          {[
            { label: 'Searches', value: stats.searches, icon: '🔍' },
            { label: 'Wishlist', value: stats.wishlist, icon: '❤️' },
            { label: 'Viewed', value: '—', icon: '👁' },
            { label: 'Alerts', value: '—', icon: '🔔' },
          ].map(({ label, value, icon }) => (
            <div className="profile-kpi-tile" key={label}>
              <div className="kpi-value">{value}</div>
              <div className="kpi-label">{icon} {label}</div>
            </div>
          ))}
        </div>

        {/* 3. Edit Profile */}
        <div className="profile-card" id="edit-profile-section">
          <div className="profile-section-title">✏️ Edit Profile</div>
          <form className="profile-form" onSubmit={handleEditSave} noValidate>
            {editErrors.form && (
              <div style={{ fontSize: '0.85rem', color: '#ef4444', padding: '0.5rem 0' }}>⚠ {editErrors.form}</div>
            )}

            <div className="profile-field">
              <label className="profile-label">Full Name</label>
              <input
                className={`profile-input${editErrors.name ? ' input-error' : ''}`}
                type="text"
                value={editName}
                onChange={e => setEditName(e.target.value)}
                placeholder="Your full name"
                disabled={editBusy}
              />
              {editErrors.name && <span className="profile-field-msg error">⚠ {editErrors.name}</span>}
            </div>

            <div className="profile-field">
              <label className="profile-label">Phone Number</label>
              <input
                className={`profile-input${editErrors.phone ? ' input-error' : ''}`}
                type="tel"
                value={editPhone}
                onChange={e => setEditPhone(e.target.value)}
                placeholder="9876543210 or +919876543210"
                disabled={editBusy}
                maxLength={13}
              />
              {editErrors.phone && <span className="profile-field-msg error">⚠ {editErrors.phone}</span>}
            </div>

            <div className="profile-field">
              <label className="profile-label">Email Address</label>
              <input
                className="profile-input readonly-field"
                type="email"
                value={user?.email || 'Email not added'}
                readOnly
                tabIndex={-1}
              />
              <span className="profile-field-msg" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                Email cannot be changed
              </span>
            </div>

            <button type="submit" className="profile-save-btn" disabled={editBusy}>
              {editBusy ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        </div>

        {/* 4. Change Password */}
        <div className="profile-card">
          <div className="profile-section-title">🔒 Change Password</div>
          <form className="profile-form" onSubmit={handlePwChange} noValidate>
            {pwErrors.form && (
              <div style={{ fontSize: '0.85rem', color: '#ef4444', padding: '0.5rem 0' }}>⚠ {pwErrors.form}</div>
            )}

            <div className="profile-field">
              <label className="profile-label">Current Password</label>
              <div className="profile-pw-wrap">
                <input
                  className={`profile-input${pwErrors.current ? ' input-error' : ''}`}
                  type={pwShow.current ? 'text' : 'password'}
                  value={pwFields.current}
                  onChange={e => setPwFields(p => ({ ...p, current: e.target.value }))}
                  placeholder="Your current password"
                  disabled={pwBusy}
                />
                <button type="button" className="pw-toggle" onClick={() => setPwShow(s => ({ ...s, current: !s.current }))} tabIndex={-1}>
                  <EyeIcon open={pwShow.current} />
                </button>
              </div>
              {pwErrors.current && <span className="profile-field-msg error">⚠ {pwErrors.current}</span>}
            </div>

            <div className="profile-field">
              <label className="profile-label">New Password</label>
              <div className="profile-pw-wrap">
                <input
                  className={`profile-input${pwErrors.newPw ? ' input-error' : ''}`}
                  type={pwShow.newPw ? 'text' : 'password'}
                  value={pwFields.newPw}
                  onChange={e => setPwFields(p => ({ ...p, newPw: e.target.value }))}
                  placeholder="Create a new strong password"
                  disabled={pwBusy}
                />
                <button type="button" className="pw-toggle" onClick={() => setPwShow(s => ({ ...s, newPw: !s.newPw }))} tabIndex={-1}>
                  <EyeIcon open={pwShow.newPw} />
                </button>
              </div>
              {pwErrors.newPw && <span className="profile-field-msg error">⚠ {pwErrors.newPw}</span>}

              {pwFields.newPw.length > 0 && newPwStrength && (
                <div className="profile-pw-strength">
                  <div className="profile-strength-track">
                    <div className="profile-strength-fill" style={{ width: `${newPwStrength.pct}%`, backgroundColor: newPwStrength.color }} />
                  </div>
                  <div className="profile-strength-label" style={{ color: newPwStrength.color }}>{newPwStrength.label}</div>
                  <div className="profile-rules">
                    {PW_RULES.map(r => (
                      <div key={r.key} className={`profile-rule${r.test(pwFields.newPw) ? ' rule-ok' : ''}`}>
                        {r.test(pwFields.newPw) ? '✓' : '○'} {r.label}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="profile-field">
              <label className="profile-label">Confirm New Password</label>
              <div className="profile-pw-wrap">
                <input
                  className={`profile-input${pwErrors.confirm ? ' input-error' : pwFields.confirm && pwFields.confirm === pwFields.newPw ? ' input-success' : ''}`}
                  type={pwShow.confirm ? 'text' : 'password'}
                  value={pwFields.confirm}
                  onChange={e => setPwFields(p => ({ ...p, confirm: e.target.value }))}
                  placeholder="Repeat new password"
                  disabled={pwBusy}
                />
                <button type="button" className="pw-toggle" onClick={() => setPwShow(s => ({ ...s, confirm: !s.confirm }))} tabIndex={-1}>
                  <EyeIcon open={pwShow.confirm} />
                </button>
              </div>
              {pwFields.confirm.length > 0 && pwFields.confirm === pwFields.newPw && (
                <span className="profile-field-msg" style={{ color: '#10b981' }}>✓ Passwords match</span>
              )}
              {pwErrors.confirm && <span className="profile-field-msg error">⚠ {pwErrors.confirm}</span>}
            </div>

            <button type="submit" className="profile-save-btn" disabled={pwBusy}>
              {pwBusy ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>

        {/* Logout */}
        <div className="profile-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
          <div className="profile-section-title" style={{ marginBottom: 0 }}>⚙️ Account</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
            Sign out from BuySmart on this device.
          </div>
          <button className="profile-logout-btn" onClick={handleLogout}>
            🚪 Sign Out
          </button>
        </div>

          </>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
