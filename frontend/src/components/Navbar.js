import React, { useState } from 'react';
import './Navbar.css';

function getInitials(name = '') {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() || '')
    .join('') || 'U';
}

const Navbar = ({ user, onAuthChange, onOpenSection, onOpenProfile, theme, onToggleTheme, activeTab }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigate = (tab) => {
    onOpenSection?.(tab);
    setMobileMenuOpen(false);
  };

  const isAdmin = user && (user.role === 'admin' || user.is_admin);


  return (
    <>
      <nav className="navbar" aria-label="Main Navigation">
        <div className="navbar-inner">
          {/* Logo */}
          <div className="navbar-left" onClick={() => navigate('home')} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && navigate('home')} aria-label="BuySmart Home">
            <div className="nav-logo-wrap">
              <div className="nav-logo-fallback">BuySmart</div>
            </div>
          </div>



          {/* Desktop nav links */}
          <div className="navbar-links">
            <button className={`navlink ${activeTab === 'home' ? 'active' : ''}`} onClick={() => navigate('home')}>Home</button>
            <button className={`navlink ${activeTab === 'search' ? 'active' : ''}`} onClick={() => navigate('search')}>Search</button>
            {user && !isAdmin && (
              <button className={`navlink ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => navigate('dashboard')}>My Activity</button>
            )}
            {isAdmin && (
              <button className={`navlink ${activeTab === 'admin-dashboard' ? 'active' : ''}`} onClick={() => navigate('admin-dashboard')}>Admin Panel</button>
            )}
          </div>

          {/* Right side */}
          <div className="navbar-right">
            <button className="nav-theme-toggle" onClick={onToggleTheme} aria-label="Toggle theme">
              {theme === 'dark' ? '🌙' : '☀️'}
            </button>

            {user ? (
              /* Logged-in: avatar pill → goes to Profile page */
              <button className={`userpill ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => navigate('profile')} id="navbar-profile-btn" aria-label="View Profile">
                <div className="user-avatar">{getInitials(user.name)}</div>
                <div className="user-info">
                  <span className="userpill-name">{user.name || 'User'}</span>
                  <span className="userpill-email">{user.email}</span>
                </div>
              </button>
            ) : (
              /* Not logged in: Login / Register buttons */
              <div className="user-actions">
                <button
                  className="navbtn"
                  id="navbar-login-btn"
                  onClick={() => navigate('login')}
                >
                  Login
                </button>
                <button
                  className="navbtn primary"
                  id="navbar-register-btn"
                  onClick={() => navigate('register')}
                >
                  Register
                </button>
              </div>
            )}

            {/* Mobile hamburger */}
            <button
              className={`nav-hamburger ${mobileMenuOpen ? 'open' : ''}`}
              onClick={() => setMobileMenuOpen(o => !o)}
              aria-label="Open Menu"
              aria-expanded={mobileMenuOpen}
            >
              <span /><span /><span />
            </button>
          </div>
        </div>

        {/* Mobile menu overlay */}
        <div className={`nav-mobile-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />

        {/* Mobile menu drawer */}
        <div className={`nav-mobile-drawer ${mobileMenuOpen ? 'open' : ''}`} role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <div className="drawer-header">
            <div className="drawer-logo">Buy<span>Smart</span></div>
            <button className="drawer-close-btn" onClick={() => setMobileMenuOpen(false)} aria-label="Close menu">✕</button>
          </div>
          <div className="drawer-content">
            <button className={`nav-mobile-link ${activeTab === 'home' ? 'active' : ''}`} onClick={() => navigate('home')}>🏠 Home</button>
            <button className={`nav-mobile-link ${activeTab === 'search' ? 'active' : ''}`} onClick={() => navigate('search')}>🔍 Search</button>

            {user ? (
              <>
                {!isAdmin && (
                  <button className={`nav-mobile-link ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => navigate('dashboard')}>🕒 My Activity</button>
                )}
                <button className={`nav-mobile-link ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => navigate('profile')}>👤 Profile</button>
                {isAdmin && (
                  <button className={`nav-mobile-link ${activeTab === 'admin-dashboard' ? 'active' : ''}`} onClick={() => navigate('admin-dashboard')}>🛡️ Admin Panel</button>
                )}
              </>
            ) : (
              <div className="drawer-auth-actions" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1rem' }}>
                <button className="nav-mobile-link" onClick={() => navigate('login')}>🔑 Login</button>
                <button className="nav-mobile-link nav-mobile-primary" onClick={() => navigate('register')}>Create Account</button>
              </div>
            )}
          </div>
        </div>
      </nav>
    </>
  );
};

export default Navbar;
