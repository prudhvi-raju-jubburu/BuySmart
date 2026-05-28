import React, { useState } from 'react';
import './ProductCard.css';
import { addToWishlist, createRedirect, getBaseUrl } from '../services/api';

const ProductCard = ({ product, user, source = 'search', searchQuery, isSelected, onToggleSelect }) => {
  const [busy, setBusy] = useState(false);

  const parseReasons = (reasonStr) => {
    if (!reasonStr) return [];
    const parts = reasonStr.split(/\s*(?:&|&amp;|\band\b)\s*/i);
    return parts.map(p => p.trim()).filter(Boolean);
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
    if (!rating) return null;
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    return (
      <span className="stars">
        {'★'.repeat(fullStars)}
        {hasHalfStar && '☆'}
        {'☆'.repeat(emptyStars)}
      </span>
    );
  };


  const platformClass = `platform-${(product.platform || 'other').toLowerCase()}`;

  const handleBuy = async () => {
    setBusy(true);
    try {
      const data = await createRedirect({
        product_id: product.id,
        source: source || 'search',
        search_query: searchQuery,
        product_data: product,
      });
      window.open(`${getBaseUrl()}${data.redirect_url}`, '_blank', 'noopener,noreferrer');
    } catch (e) {
      if (product.product_url) {
        window.open(product.product_url, '_blank', 'noopener,noreferrer');
      } else {
        window.showToast?.('Product link not available', 'info');
      }
    } finally {
      setBusy(false);
    }
  };

  const handleWishlist = async (e) => {
    e.stopPropagation();
    if (!user) {
      window.showToast?.('Please login to save products', 'warning');
      return;
    }
    setBusy(true);
    try {
      await addToWishlist(product.id, { product_data: product });
      window.showToast?.('Added to wishlist!', 'success');
    } catch (e) {
      window.showToast?.(e?.response?.data?.error || 'Wishlist failed', 'error');
    } finally {
      setBusy(false);
    }
  };

  const reasonsList = parseReasons(product.reason);

  return (
    <div className={`product-card ${isSelected ? 'selected' : ''}`}>
      <div className="product-selection-overlay">
        <label className="compare-checkbox" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={!!isSelected}
            onChange={() => onToggleSelect(product)}
          />
          Compare
        </label>
      </div>

      <div className={`product-platform-badge ${platformClass}`}>
        {product.platform}
      </div>

      <div className="product-image-container">
        <img
          src={product.image_url || 'https://via.placeholder.com/200?text=No+Image'}
          alt={product.name}
          className="product-image"
          loading="lazy"
          onError={(e) => {
            if (!e.target.src.includes('placeholder')) {
              e.target.src = 'https://via.placeholder.com/200?text=No+Image';
            }
          }}
        />
      </div>

      <div className="product-info">
        <h3 className="product-name" title={product.name}>
          {product.name || 'Unknown Product'}
        </h3>

        {reasonsList.length > 0 && (
          <div className="product-recommendation-reasons">
            <span className="recommendation-header">💡 Why Recommended</span>
            <ul className="recommendation-list">
              {reasonsList.map((r, i) => (
                <li key={i}>✓ {r}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="price-container">
          <span className="current-price">{formatINR(product.price)}</span>
          {product.original_price && product.original_price > product.price && (
            <span className="original-price">{formatINR(product.original_price)}</span>
          )}
        </div>

        {product.rating && (
          <div className="rating-bar">
            {renderStars(product.rating)}
            <span className="rating-count">
              {product.rating.toFixed(1)} ({product.review_count?.toLocaleString()} reviews)
            </span>
          </div>
        )}

        <div className="action-buttons">
          <button className="view-deal-btn" onClick={handleBuy} disabled={busy}>
            View Deal
          </button>
          <button className="wishlist-btn" onClick={handleWishlist} disabled={busy}>
            ❤️
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;


