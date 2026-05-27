import React, { useEffect, useState } from 'react';
import { getDashboardWishlist, removeFromWishlist, createRedirect, getBaseUrl } from '../../services/api';
import { SkeletonCard } from '../SkeletonCard';

const WishlistPanel = ({ user }) => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [sortBy, setSortBy] = useState('date_added');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const fetchWishlist = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardWishlist(sortBy);
      if (res.success) {
        setItems(res.data.items || []);
        setStats(res.data.stats || null);
      } else {
        setError(res.message || 'Failed to load wishlist items');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error loading wishlist items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWishlist();
  }, [sortBy]);

  const handleRemove = async (productId) => {
    if (!window.confirm('Remove this product from your wishlist?')) return;
    setBusyId(productId);
    try {
      const res = await removeFromWishlist(productId);
      if (res.success || res.status === 'success') {
        fetchWishlist();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to remove product');
    } finally {
      setBusyId(null);
    }
  };

  const handleBuy = async (product) => {
    try {
      const data = await createRedirect({
        product_id: product.id,
        source: 'wishlist',
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

  const renderStars = (rating) => {
    if (!rating) return 'No rating';
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    return (
      <span className="wish-stars">
        {'★'.repeat(fullStars)}
        {hasHalfStar && '☆'}
        <span className="wish-rating-value"> {rating.toFixed(1)}</span>
      </span>
    );
  };

  return (
    <div className="wishlist-panel-container animate-fade-in">
      <div className="panel-header-row">
        <div className="panel-header">
          <h3 className="card-title">Wishlist Management</h3>
          <span className="subtitle-desc">Manage your saved products and view stats</span>
        </div>
        <div className="sort-controls">
          <label htmlFor="wishlist-sort">Sort By: </label>
          <select
            id="wishlist-sort"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="wishlist-sort-select"
          >
            <option value="date_added">Date Added</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="rating">Rating</option>
          </select>
        </div>
      </div>

      {/* Stats Summary Section */}
      {stats && stats.total_items > 0 && (
        <div className="wishlist-stats-grid">
          <div className="wish-stat-card">
            <span className="w-stat-label">Total Items</span>
            <span className="w-stat-value">{stats.total_items}</span>
          </div>
          <div className="wish-stat-card">
            <span className="w-stat-label">Average Price</span>
            <span className="w-stat-value">{formatINR(stats.average_price)}</span>
          </div>
          <div className="wish-stat-card">
            <span className="w-stat-label">Average Rating</span>
            <span className="w-stat-value">⭐ {stats.average_rating.toFixed(1)}</span>
          </div>
          {stats.highest_rated_item && (
            <div className="wish-stat-card linkable" onClick={() => handleBuy(stats.highest_rated_item)}>
              <span className="w-stat-label">Highest Rated</span>
              <span className="w-stat-value text-truncate" title={stats.highest_rated_item.name}>
                {stats.highest_rated_item.name}
              </span>
              <span className="w-stat-sub">⭐ {stats.highest_rated_item.rating.toFixed(1)}</span>
            </div>
          )}
          {stats.lowest_price_item && (
            <div className="wish-stat-card linkable" onClick={() => handleBuy(stats.lowest_price_item)}>
              <span className="w-stat-label">Lowest Price</span>
              <span className="w-stat-value text-truncate" title={stats.lowest_price_item.name}>
                {stats.lowest_price_item.name}
              </span>
              <span className="w-stat-sub">{formatINR(stats.lowest_price_item.price)}</span>
            </div>
          )}
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="wishlist-items-grid">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : items.length > 0 ? (
        <div className="wishlist-items-grid">
          {items.map((item) => {
            const product = item.product;
            if (!product) return null;
            return (
              <div key={item.id} className="wish-product-card">
                <div className={`wish-product-badge platform-${product.platform.toLowerCase()}`}>
                  {product.platform}
                </div>
                <div className="wish-product-img-container">
                  <img
                    src={product.image_url || 'https://via.placeholder.com/150?text=No+Image'}
                    alt={product.name}
                    className="wish-product-img"
                    onError={(e) => {
                      if (!e.target.src.includes('placeholder')) {
                        e.target.src = 'https://via.placeholder.com/150?text=No+Image';
                      }
                    }}
                  />
                </div>
                <div className="wish-product-info">
                  <h4 className="wish-product-name" title={product.name}>
                    {product.name}
                  </h4>
                  <div className="wish-product-price-row">
                    <span className="wish-current-price">{formatINR(product.price)}</span>
                    {product.original_price && product.original_price > product.price && (
                      <span className="wish-orig-price">{formatINR(product.original_price)}</span>
                    )}
                  </div>
                  <div className="wish-product-rating">
                    {renderStars(product.rating)}
                  </div>
                  <div className="wish-product-actions">
                    <button
                      className="wish-action-btn buy"
                      onClick={() => handleBuy(product)}
                    >
                      View Deal
                    </button>
                    <button
                      className="wish-action-btn delete"
                      disabled={busyId === product.id}
                      onClick={() => handleRemove(product.id)}
                    >
                      {busyId === product.id ? 'Removing...' : '🗑️ Remove'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4rem 2rem', color: 'var(--text-dim)' }}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '1rem', color: 'var(--primary)' }}>
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
          <h4 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>No wishlist items yet.</h4>
          <p style={{ textAlign: 'center', maxWidth: '300px' }}>Start exploring products and save items you like.</p>
        </div>
      )}
    </div>
  );
};

export default WishlistPanel;
