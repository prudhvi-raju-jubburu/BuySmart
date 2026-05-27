import React, { useEffect, useState } from 'react';
import { getDashboardPreferences } from '../../services/api';

const PreferenceInsights = () => {
  const [prefs, setPrefs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPrefs = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getDashboardPreferences();
        if (res.success) {
          setPrefs(res.data);
        } else {
          setError(res.message || 'Failed to load preferences profile');
        }
      } catch (err) {
        setError(err.response?.data?.message || 'Error loading preferences profile');
      } finally {
        setLoading(false);
      }
    };

    fetchPrefs();
  }, []);

  if (loading) {
    return (
      <div className="panel-loading">
        <div className="spinner"></div>
        <span>Assembling your shopping preferences profile...</span>
      </div>
    );
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!prefs) return null;

  return (
    <div className="preference-insights-container animate-fade-in">
      <div className="panel-header">
        <h3 className="card-title">Preference Insights</h3>
        <span className="subtitle-desc">AI-generated overview of your shopping patterns and profile</span>
      </div>

      <div className="shopping-profile-grid">
        {/* Your Shopping Profile Main Card */}
        <div className="profile-summary-card">
          <div className="profile-card-header-gradient">
            <span className="profile-avatar-emoji">🧠</span>
            <div className="profile-header-details">
              <h4>Your Shopping Profile</h4>
              <span>Automatically computed from your views and wishlist</span>
            </div>
          </div>

          <div className="profile-attribute-list">
            {/* Categories */}
            <div className="attribute-row">
              <span className="attribute-label">Preferred Categories</span>
              <div className="attribute-value-tags">
                {prefs.preferred_categories && prefs.preferred_categories.length > 0 ? (
                  prefs.preferred_categories.map((cat, idx) => (
                    <span key={idx} className="pref-badge category">
                      🏷️ {cat}
                    </span>
                  ))
                ) : (
                  <span className="no-pref-text">No category data yet</span>
                )}
              </div>
            </div>

            {/* Platforms */}
            <div className="attribute-row">
              <span className="attribute-label">Preferred Platforms</span>
              <div className="attribute-value-tags">
                {prefs.preferred_platforms && prefs.preferred_platforms.length > 0 ? (
                  prefs.preferred_platforms.map((plat, idx) => (
                    <span key={idx} className={`pref-badge platform platform-${plat.toLowerCase()}`}>
                      🔌 {plat}
                    </span>
                  ))
                ) : (
                  <span className="no-pref-text">No platform data yet</span>
                )}
              </div>
            </div>

            {/* Price Range */}
            <div className="attribute-row">
              <span className="attribute-label">Preferred Price Range</span>
              <div className="attribute-value-tags">
                <span className="pref-badge price-range">
                  💰 {prefs.preferred_price_range || '₹10,000 - ₹30,000'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recommendation Engine Metrics */}
        <div className="engine-metrics-card">
          <div className="engine-card-header">
            <span className="engine-icon">✨</span>
            <div className="engine-header-details">
              <h4>AI Recommendation Engine Engagement</h4>
              <span>Upgraded personal matching insights</span>
            </div>
          </div>

          <div className="engine-stats-grid">
            <div className="engine-stat-item pink">
              <span className="engine-stat-val">{prefs.recommendations_clicked}</span>
              <span className="engine-stat-lbl">Recommendations Clicked</span>
            </div>
            
            <div className="engine-stat-item teal">
              <span className="engine-stat-val">{(prefs.recommendation_ctr * 100).toFixed(1)}%</span>
              <span className="engine-stat-lbl">Recommendation CTR</span>
            </div>

            <div className="engine-stat-item purple">
              <span className="engine-stat-val text-truncate" title={prefs.top_recommended_category}>
                {prefs.top_recommended_category || 'N/A'}
              </span>
              <span className="engine-stat-lbl">Top Recommended Category</span>
            </div>
          </div>

          <div className="engine-info-note">
            <p>💡 <strong>Personalized Feed:</strong> BuySmart's AI model utilizes these metrics to customize your Home Recommendations feed for optimal product discoveries.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PreferenceInsights;
