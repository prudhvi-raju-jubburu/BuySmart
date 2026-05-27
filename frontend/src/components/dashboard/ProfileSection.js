import React, { useState } from 'react';
import { updateProfile } from '../../services/api';

const ProfileSection = ({ user, onProfileUpdate }) => {
  const [name, setName] = useState(user?.name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const formatDate = (isoStr) => {
    if (!isoStr) return 'Never';
    return new Date(isoStr).toLocaleString();
  };

  const handleUpdateName = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setMessage({ type: 'error', text: 'Name cannot be empty' });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const res = await updateProfile({ name: name.trim() });
      if (res.success) {
        setMessage({ type: 'success', text: 'Display name updated successfully!' });
        if (onProfileUpdate) {
          onProfileUpdate(res.data.user);
        }
      } else {
        setMessage({ type: 'error', text: res.message || 'Failed to update profile' });
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.message || 'Error occurred updating profile'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!currentPassword) {
      setMessage({ type: 'error', text: 'Current password is required' });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({ type: 'error', text: 'New password must be at least 6 characters' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const res = await updateProfile({
        current_password: currentPassword,
        new_password: newPassword
      });
      if (res.success) {
        setMessage({ type: 'success', text: 'Password changed successfully!' });
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        if (onProfileUpdate) {
          onProfileUpdate(res.data.user);
        }
      } else {
        setMessage({ type: 'error', text: res.message || 'Failed to change password' });
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.message || 'Error occurred changing password'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-section-container animate-fade-in">
      <div className="profile-info-grid">
        {/* Account Info Details */}
        <div className="profile-card info-card">
          <h3 className="card-title">Account Details</h3>
          <div className="details-list">
            <div className="detail-item">
              <span className="detail-label">Email Address</span>
              <span className="detail-value bold">{user?.email}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">User Role</span>
              <span className="detail-value role-badge">{user?.role?.toUpperCase()}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Account Status</span>
              <span className={`detail-value status-badge ${user?.is_active ? 'active' : 'disabled'}`}>
                {user?.is_active ? 'Active' : 'Disabled'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Member Since</span>
              <span className="detail-value">{formatDate(user?.created_at)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Last Login</span>
              <span className="detail-value">{formatDate(user?.last_login)}</span>
            </div>
          </div>
        </div>

        {/* Update Name Form */}
        <div className="profile-card form-card">
          <h3 className="card-title">Update Profile Info</h3>
          {message.text && (
            <div className={`form-message ${message.type}`}>
              {message.text}
            </div>
          )}
          
          <form onSubmit={handleUpdateName} className="profile-form">
            <div className="form-group">
              <label htmlFor="name-input">Display Name</label>
              <input
                id="name-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                className="profile-input"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading || name === user?.name}
              className="profile-btn primary"
            >
              {loading ? 'Saving...' : 'Update Name'}
            </button>
          </form>

          {/* Change Password Form */}
          <h3 className="card-title" style={{ marginTop: '24px' }}>Change Password</h3>
          <form onSubmit={handleChangePassword} className="profile-form">
            <div className="form-group">
              <label htmlFor="current-pw">Current Password</label>
              <input
                id="current-pw"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="profile-input"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="new-pw">New Password</label>
              <input
                id="new-pw"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 6 characters"
                className="profile-input"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="confirm-pw">Confirm New Password</label>
              <input
                id="confirm-pw"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                className="profile-input"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading || !currentPassword || !newPassword}
              className="profile-btn secondary"
            >
              {loading ? 'Updating...' : 'Change Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfileSection;
