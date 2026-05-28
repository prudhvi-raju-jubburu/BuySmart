import React, { useState, useEffect } from 'react';
import { SkeletonCard } from '../SkeletonCard';
import { 
  getPersonalizedRecommendations, 
  submitRecommendationFeedback, 
  createRedirect, 
  addToWishlist, 
  getBaseUrl 
} from '../../services/api';
import './PersonalizedRecommendations.css';

const PersonalizedRecommendations = ({ user }) => {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedbackStatus, setFeedbackStatus] = useState({}); // Stores feedback status (liked/hidden/saved) per product id
  const [fadeProducts, setFadeProducts] = useState({}); // Animates hidden/disliked products fading out

  useEffect(() => {
    fetchRecs();
  }, [user]);

  const fetchRecs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPersonalizedRecommendations();
      if (res.success) {
        setRecommendations(res.data);
      } else {
        setError(res.message || 'Failed to load recommendations.');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error loading recommendations.');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (productId, feedbackType) => {
    try {
      // Opt-in UI update for hide/dislike
      if (feedbackType === 'not_interested') {
        // Fade out
        setFadeProducts(prev => ({ ...prev, [productId]: true }));
        
        // Wait for animation to finish before calling API
        setTimeout(async () => {
          try {
            await submitRecommendationFeedback(productId, feedbackType);
            // Remove from state lists
            setRecommendations(prev => {
              if (!prev) return null;
              const cleanRecs = {};
              Object.keys(prev).forEach(railKey => {
                cleanRecs[railKey] = prev[railKey].filter(item => item.product.id !== productId);
              });
              return cleanRecs;
            });
          } catch (e) {
            console.error(e);
          }
        }, 500);
      } else {
        // Like or Save for Later
        await submitRecommendationFeedback(productId, feedbackType);
        setFeedbackStatus(prev => ({ ...prev, [productId]: feedbackType }));
        window.showToast?.(feedbackType === 'like' ? '👍 Liked! We will recommend more items like this.' : '💾 Saved for Later!', 'success');
      }
    } catch (err) {
      window.showToast?.(err.response?.data?.message || 'Feedback submission failed', 'error');
    }
  };

  const handleBuy = async (product) => {
    try {
      const data = await createRedirect({
        product_id: product.id,
        source: 'recommendation',
        product_data: product,
      });
      window.open(`${getBaseUrl()}${data.redirect_url}`, '_blank', 'noopener,noreferrer');
    } catch (e) {
      if (product.product_url) {
        window.open(product.product_url, '_blank', 'noopener,noreferrer');
      } else {
        window.showToast?.('Product URL not available.', 'error');
      }
    }
  };

  const handleAddWishlist = async (productId, product) => {
    try {
      await addToWishlist(productId, { product_data: product });
      window.showToast?.('❤️ Product added to your wishlist!', 'success');
    } catch (e) {
      window.showToast?.(e.response?.data?.error || 'Failed to add to wishlist', 'error');
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val || 0);
  };

  const renderProductCard = (item, index) => {
    const { product, reason, breakdown } = item;
    const isFaded = fadeProducts[product.id];
    const status = feedbackStatus[product.id];
    
    return (
      <div 
        key={`${product.id}-${index}`} 
        className={`rec-card-item ${isFaded ? 'fade-out' : ''}`}
      >
        {/* Explainability Tag */}
        {reason && (
          <div className="rec-explanation-banner">
            <span className="rec-explanation-icon">💡</span>
            <span className="rec-explanation-text">{reason}</span>
          </div>
        )}

        <div className={`rec-platform-badge platform-${product.platform.toLowerCase()}`}>
          {product.platform}
        </div>

        <div className="rec-img-container">
          <img 
            src={product.image_url || 'https://via.placeholder.com/150?text=BuySmart'} 
            alt={product.name} 
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = 'https://via.placeholder.com/150?text=Product';
            }}
          />
        </div>

        <div className="rec-details">
          <h4 className="rec-name" title={product.name}>{product.name}</h4>
          
          <div className="rec-meta">
            <span className="rec-price">{formatCurrency(product.price)}</span>
            {product.rating && (
              <span className="rec-rating">
                ★ {product.rating} 
                <span className="rec-reviews-count">({product.review_count})</span>
              </span>
            )}
          </div>

          {/* Interactive Score Breakdown Tooltip Hidden for Non-Technical Users */}

          {/* Action Footer Buttons */}
          <div className="rec-actions-footer">
            <button 
              className="rec-btn-buy" 
              onClick={() => handleBuy(product)}
            >
              Compare Prices
            </button>
            <button 
              className="rec-btn-wish"
              onClick={() => handleAddWishlist(product.id, product)}
              title="Add to Wishlist"
            >
              ❤️
            </button>
          </div>

          {/* Feedback buttons */}
          {!user ? null : (
            <div className="rec-feedback-bar">
              <button 
                className={`feedback-btn btn-like ${status === 'like' ? 'active' : ''}`}
                onClick={() => handleFeedback(product.id, 'like')}
                title="Like this recommendation"
              >
                👍
              </button>
              <button 
                className={`feedback-btn btn-save ${status === 'save_for_later' ? 'active' : ''}`}
                onClick={() => handleFeedback(product.id, 'save_for_later')}
                title="Save recommendation for later"
              >
                💾
              </button>
              <button 
                className="feedback-btn btn-dislike"
                onClick={() => handleFeedback(product.id, 'not_interested')}
                title="Not interested (hide this product)"
              >
                🚫
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderRail = (title, items, isColdStart = false) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="rec-rail-section">
        <h3 className="rec-rail-title">
          {title} {isColdStart && <span className="coldstart-badge">Global Popular</span>}
        </h3>
        <div className="rec-rail-grid scroll-bar-styled">
          {items.map((item, idx) => renderProductCard(item, idx))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="personalized-recommendations-container">
        <div className="panel-header">
          <h2 className="card-title">Recommendations For You 🌟</h2>
          <p className="subtitle-desc">Compiling your personalized shopping profile...</p>
        </div>
        <div className="recommendations-rails-wrapper">
          <div className="rec-rail-section">
            <div className="rec-rail-grid scroll-bar-styled" style={{ display: 'flex', gap: '1rem' }}>
              {[...Array(5)].map((_, i) => (
                <div key={i} style={{ width: '280px', flexShrink: 0 }}>
                  <SkeletonCard />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendations-error-tab">
        <div className="error-message">{error}</div>
        <button className="btn btn-secondary" onClick={fetchRecs} style={{ marginTop: '1rem' }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="personalized-recommendations-container">
      <div className="panel-header">
        <h2 className="card-title">Recommendations For You 🌟</h2>
        <p className="subtitle-desc">
          {!user 
            ? "Showing popular items. Log in to experience personalized recommendations!"
            : "Recommendations custom-tailored based on your search history, clicks, wishlists, and purchases."}
        </p>
      </div>

      {recommendations && Object.keys(recommendations).length > 0 ? (
        <div className="recommendations-rails-wrapper">
          {/* Personalized Rails */}
          {recommendations.recommended_for_you && renderRail("Recommended For You", recommendations.recommended_for_you)}
          {recommendations.trending_in_your_interests && renderRail("Trending In Your Interests", recommendations.trending_in_your_interests)}
          {recommendations.recently_similar && renderRail("Recently Similar Products", recommendations.recently_similar)}

          {/* Onboarding Cold-Start Rails */}
          {recommendations.popular_electronics && renderRail("Popular Electronics", recommendations.popular_electronics, true)}
          {recommendations.popular_fashion && renderRail("Popular Fashion", recommendations.popular_fashion, true)}
          {recommendations.popular_mobiles && renderRail("Popular Mobiles", recommendations.popular_mobiles, true)}
          {recommendations.best_rated && renderRail("Best Rated Products", recommendations.best_rated, true)}
          {recommendations.most_wishlisted && renderRail("Most Wishlisted Products", recommendations.most_wishlisted, true)}
        </div>
      ) : (
        <div className="empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4rem 2rem', color: 'var(--text-dim)' }}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '1rem', color: 'var(--primary)' }}>
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
          <h4 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>No recommendations yet</h4>
          <p style={{ textAlign: 'center', maxWidth: '300px' }}>Try searching for products or viewing items to get personalized recommendations.</p>
        </div>
      )}
    </div>
  );
};

export default PersonalizedRecommendations;
