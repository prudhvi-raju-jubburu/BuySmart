import React from 'react';

const IntentSummary = ({ intent, confidence }) => {
  if (!intent) return null;

  const formatCurrency = (val) => {
    if (val === null || val === undefined) return null;
    try {
      return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
    } catch (e) {
      return `₹${val}`;
    }
  };

  const budget = (intent.budget_min || intent.budget_max)
    ? `${intent.budget_min ? formatCurrency(intent.budget_min) : '₹0'} – ${intent.budget_max ? formatCurrency(intent.budget_max) : 'Any'}`
    : intent.budget_max ? `Under ${formatCurrency(intent.budget_max)}` : null;

  return (
    <div className="intent-summary-card glass-card">
      <div className="intent-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.1rem' }}>🛍️</span>
          <h3>Shopping Summary</h3>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginTop: '0.5rem' }}>
        {intent.category && (
          <div className="intent-item" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <span className="intent-label" style={{ color: 'var(--text-dim)', fontWeight: '500' }}>Looking For:</span>
            <span className="intent-value" style={{ color: 'var(--text-main)', fontWeight: '600' }}>{intent.category}</span>
          </div>
        )}
        
        {intent.brand && (
          <div className="intent-item" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <span className="intent-label" style={{ color: 'var(--text-dim)', fontWeight: '500' }}>Brand:</span>
            <span className="intent-value" style={{ color: 'var(--text-main)', fontWeight: '600' }}>{intent.brand}</span>
          </div>
        )}

        {budget && (
          <div className="intent-item" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <span className="intent-label" style={{ color: 'var(--text-dim)', fontWeight: '500' }}>Budget:</span>
            <span className="intent-value" style={{ color: 'var(--text-main)', fontWeight: '600' }}>{budget}</span>
          </div>
        )}

        {intent.purpose && (
          <div className="intent-item" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <span className="intent-label" style={{ color: 'var(--text-dim)', fontWeight: '500' }}>Purpose:</span>
            <span className="intent-value" style={{ color: 'var(--text-main)', fontWeight: '600' }}>{intent.purpose}</span>
          </div>
        )}

        {intent.features && intent.features.length > 0 && (
          <div className="intent-item" style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', alignItems: 'flex-start' }}>
            <span className="intent-label" style={{ color: 'var(--text-dim)', fontWeight: '500' }}>Key Features:</span>
            <span className="intent-value" style={{ color: 'var(--text-main)', fontWeight: '600' }}>{intent.features.join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntentSummary;
