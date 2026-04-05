import React, { useState } from 'react';
import './ProductCard.css';
import { addToWishlist, createRedirect, confirmPurchase, getProductPriceHistory } from '../services/api';
import Modal from './Modal';
import PriceHistoryChart from './PriceHistoryChart';

const ProductCard = ({ product, user, source = 'search', searchQuery, isSelected, onToggleSelect }) => {
  const [busy, setBusy] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [historyData, setHistoryData] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

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
      window.open(`http://localhost:5000${data.redirect_url}`, '_blank', 'noopener,noreferrer');
    } catch (e) {
      if (product.product_url) {
        window.open(product.product_url, '_blank', 'noopener,noreferrer');
      } else {
        alert('Product link not available');
      }
    } finally {
      setBusy(false);
    }
  };

  const handleWishlist = async (e) => {
    e.stopPropagation();
    if (!user) {
      alert('Please login to save products');
      return;
    }
    setBusy(true);
    try {
      await addToWishlist(product.id, { product_data: product });
      alert('✅ Added to wishlist!');
    } catch (e) {
      alert(e?.response?.data?.error || 'Wishlist failed');
    } finally {
      setBusy(false);
    }
  };

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


