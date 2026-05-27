import React, { useEffect, useState } from 'react';
import { getDashboardPriceAlerts, updatePriceAlert, deletePriceAlert, createRedirect, getBaseUrl } from '../../services/api';
import { SkeletonRow } from '../SkeletonCard';

const PriceAlertPanel = () => {
  const [alerts, setAlerts] = useState([]);
  const [activeCount, setActiveCount] = useState(0);
  const [triggeredCount, setTriggeredCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Track editing state per alert ID
  const [editingId, setEditingId] = useState(null);
  const [editPrice, setEditPrice] = useState('');
  const [saveLoading, setSaveLoading] = useState(false);

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardPriceAlerts();
      if (res.success) {
        setAlerts(res.data.alerts || []);
        setActiveCount(res.data.active_count || 0);
        setTriggeredCount(res.data.triggered_count || 0);
      } else {
        setError(res.message || 'Failed to load price alerts');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error loading price alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleDelete = async (alertId) => {
    if (!window.confirm('Are you sure you want to delete this price drop alert?')) return;
    try {
      const res = await deletePriceAlert(alertId);
      if (res.success) {
        fetchAlerts();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete price alert');
    }
  };

  const handleEditClick = (alert) => {
    setEditingId(alert.id);
    setEditPrice(alert.target_price.toString());
  };

  const handleSaveEdit = async (alertId) => {
    const parsedPrice = parseFloat(editPrice);
    if (isNaN(parsedPrice) || parsedPrice <= 0) {
      alert('Please enter a valid target price greater than 0');
      return;
    }
    setSaveLoading(true);
    try {
      const res = await updatePriceAlert(alertId, parsedPrice);
      if (res.success) {
        setEditingId(null);
        fetchAlerts();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to update price alert');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleBuy = async (product) => {
    try {
      const data = await createRedirect({
        product_id: product.id,
        source: 'price_alert',
        search_query: '',
        product_data: product,
      });
      window.open(`${getBaseUrl()}${data.redirect_url}`, '_blank', 'noopener,noreferrer');
    } catch (e) {
      if (product.product_url) {
        window.open(product.product_url, '_blank', 'noopener,noreferrer');
      } else {
        alert('Product link not available');
      }
    }
  };

  const formatINR = (value) => {
    const n = Number(value || 0);
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(n);
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    return new Date(isoStr).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="price-alerts-panel-container animate-fade-in">
      <div className="panel-header">
        <h3 className="card-title">Price Alert Center</h3>
        <span className="subtitle-desc">Get notified immediately when prices fall below your target</span>
      </div>

      {/* Counts Summary */}
      <div className="alerts-summary-row">
        <div className="alert-sum-card active-alerts">
          <div className="sum-icon">🔔</div>
          <div className="sum-detail">
            <span className="sum-count">{activeCount}</span>
            <span className="sum-label">Active Monitors</span>
          </div>
        </div>
        <div className="alert-sum-card triggered-alerts">
          <div className="sum-icon">🎉</div>
          <div className="sum-detail">
            <span className="sum-count">{triggeredCount}</span>
            <span className="sum-label">Triggered Alerts</span>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      ) : alerts.length > 0 ? (
        <div className="alerts-list">
          {alerts.map((alertItem) => {
            const product = alertItem.product;
            if (!product) return null;
            const isEditing = editingId === alertItem.id;
            const isTriggered = alertItem.triggered_at !== null;

            return (
              <div key={alertItem.id} className={`alert-card-row ${isTriggered ? 'triggered' : ''}`}>
                <div className="alert-product-info-col">
                  <img
                    src={product.image_url || 'https://via.placeholder.com/80?text=No+Image'}
                    alt={product.name}
                    className="alert-prod-thumb"
                    onError={(e) => {
                      if (!e.target.src.includes('placeholder')) {
                        e.target.src = 'https://via.placeholder.com/80?text=No+Image';
                      }
                    }}
                  />
                  <div className="alert-metadata">
                    <span className={`alert-platform-tag platform-${product.platform.toLowerCase()}`}>
                      {product.platform}
                    </span>
                    <h4 className="alert-prod-name" title={product.name}>
                      {product.name}
                    </h4>
                  </div>
                </div>

                <div className="alert-pricing-col">
                  <div className="price-item">
                    <span className="price-label">Current Price</span>
                    <span className="price-val bold">{formatINR(product.price)}</span>
                  </div>

                  <div className="price-item">
                    <span className="price-label">Target Price</span>
                    {isEditing ? (
                      <div className="alert-edit-input-wrapper">
                        <span className="currency-prefix">₹</span>
                        <input
                          type="number"
                          value={editPrice}
                          onChange={(e) => setEditPrice(e.target.value)}
                          className="alert-price-input"
                          min="1"
                          required
                        />
                      </div>
                    ) : (
                      <span className="price-val target bold">{formatINR(alertItem.target_price)}</span>
                    )}
                  </div>
                </div>

                <div className="alert-status-col">
                  {isTriggered ? (
                    <div className="status-badge triggered">
                      <span className="status-dot"></span>
                      <span className="status-text">Dropped on {formatDate(alertItem.triggered_at)}</span>
                    </div>
                  ) : (
                    <div className="status-badge active">
                      <span className="status-dot"></span>
                      <span className="status-text">Active Monitor</span>
                    </div>
                  )}
                  <span className="created-date">Created {formatDate(alertItem.created_at)}</span>
                </div>

                <div className="alert-actions-col">
                  {isEditing ? (
                    <div className="edit-action-buttons">
                      <button
                        className="alert-btn save"
                        onClick={() => handleSaveEdit(alertItem.id)}
                        disabled={saveLoading}
                      >
                        {saveLoading ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        className="alert-btn cancel"
                        onClick={() => setEditingId(null)}
                        disabled={saveLoading}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="standard-action-buttons">
                      <button className="alert-btn deal" onClick={() => handleBuy(product)}>
                        View Deal
                      </button>
                      <button className="alert-btn edit" onClick={() => handleEditClick(alertItem)}>
                        ✏️ Edit Target
                      </button>
                      <button className="alert-btn delete" onClick={() => handleDelete(alertItem.id)}>
                        🗑️ Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4rem 2rem', color: 'var(--text-dim)' }}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '1rem', color: 'var(--primary)' }}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
          <h4 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>No Price Alerts Set</h4>
          <p style={{ textAlign: 'center', maxWidth: '300px' }}>Look for the "Set Price Alert" option on products to get notified when prices drop.</p>
        </div>
      )}
    </div>
  );
};

export default PriceAlertPanel;
