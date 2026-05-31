import React, { useState, useEffect } from 'react';
import ProductCard from './ProductCard';
import './ProductGrid.css';

const ProductGrid = ({ products, searchQuery, user, selectedProducts, onToggleSelect, isAi, platformStatus }) => {
  const [visibleCount, setVisibleCount] = useState(20);
  const [sortBy, setSortBy] = useState('relevance');

  // Reset pagination and sorting on every new search or products change
  useEffect(() => {
    setVisibleCount(20);
    setSortBy('relevance');
  }, [products]);

  console.log("Rendered Product Count:", products.length);

  const statusValues = platformStatus ? Object.values(platformStatus) : [];
  const hasFailures = statusValues.some(status => status === 'failed' || status === 'timeout');
  const allFailed = statusValues.length > 0 && statusValues.every(status => status === 'failed' || status === 'timeout');

  if (products.length === 0 && searchQuery) {
    if (allFailed) {
      return (
        <div className="no-results">
          <h2>⚠️ System Error</h2>
          <p>Live product scanning is temporarily unavailable. Please retry in a few moments.</p>
          <div className="alert-info" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px' }}>
            <p>💡 <strong>Tip:</strong> The live scanning workers are currently offline or busy. Please try again soon.</p>
          </div>
        </div>
      );
    }
    
    return (
      <div className="no-results">
        <div className="empty-state-illustration" style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>🔍</div>
        <h2>No products found</h2>
        <div style={{ marginTop: '1rem', textAlign: 'left', display: 'inline-block', color: 'var(--text-dim)' }}>
          <p>Try:</p>
          <ul style={{ paddingLeft: '1.5rem', marginTop: '0.5rem', lineHeight: '1.8', listStyleType: 'none' }}>
            <li>• Different keywords</li>
            <li>• Broader search terms</li>
            <li>• Removing filters</li>
          </ul>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="no-results" style={{ marginTop: '2rem' }}>
        <div className="empty-state-illustration" style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>☀️</div>
        <h2>Top Picks For You</h2>
        <p>Type what you want to buy in the search box above to find the best deals.</p>
      </div>
    );
  }

  // Client-side sorting before pagination
  const getSortedProducts = () => {
    if (sortBy === 'relevance') {
      return products;
    }

    return [...products].sort((a, b) => {
      const priceA = parseFloat(a.price) || 0;
      const priceB = parseFloat(b.price) || 0;
      const ratingA = parseFloat(a.rating) || 0;
      const ratingB = parseFloat(b.rating) || 0;

      const origA = parseFloat(a.original_price) || priceA;
      const origB = parseFloat(b.original_price) || priceB;
      const discA = origA > priceA ? (origA - priceA) / origA : 0;
      const discB = origB > priceB ? (origB - priceB) / origB : 0;

      if (sortBy === 'price-low-high') {
        return priceA - priceB;
      }
      if (sortBy === 'price-high-low') {
        return priceB - priceA;
      }
      if (sortBy === 'rating') {
        return ratingB - ratingA;
      }
      if (sortBy === 'discount') {
        return discB - discA;
      }
      return 0;
    });
  };

  const sortedProducts = getSortedProducts();
  const visibleProducts = sortedProducts.slice(0, visibleCount);

  return (
    <div className="product-grid-container">
      {hasFailures && (
        <div className="partial-failure-banner" style={{
          background: 'rgba(217, 119, 6, 0.15)',
          border: '1px solid rgba(217, 119, 6, 0.3)',
          borderRadius: '12px',
          padding: '1rem',
          marginBottom: '1.5rem',
          color: '#f59e0b',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.95rem'
        }}>
          <span>⚠️</span>
          <span>Some stores are temporarily unavailable. Showing available results.</span>
        </div>
      )}
      
      <div className="grid-header">
        <div className="results-count">
          {isAi ? (
            <span>✨ Suggested For You ({products.length} found)</span>
          ) : searchQuery ? (
            <span>Search Results for "{searchQuery}" ({products.length} products)</span>
          ) : (
            <span>☀️ Top Picks For You</span>
          )}
        </div>

        {products.length > 0 && (
          <div className="sort-dropdown-container">
            <label htmlFor="sort-select" className="sort-dropdown-label">Sort By:</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="sort-dropdown-select"
            >
              <option value="relevance">Relevance</option>
              <option value="price-low-high">Price: Low → High</option>
              <option value="price-high-low">Price: High → Low</option>
              <option value="rating">Rating</option>
              <option value="discount">Best Discount</option>
            </select>
          </div>
        )}
      </div>
      <div className="product-grid">
        {visibleProducts.map((product) => {
          return (
            <div key={product.id} style={{ position: 'relative' }}>
              <ProductCard
                product={product}
                user={user}
                source={isAi ? "ai-search" : "search"}
                searchQuery={searchQuery}
                isSelected={selectedProducts?.some(p => p.id === product.id)}
                onToggleSelect={onToggleSelect}
              />
            </div>
          );
        })}
      </div>
      {products.length > visibleCount && (
        <div className="load-more-container" style={{ display: 'flex', justifyContent: 'center', marginTop: '3rem' }}>
          <button 
            className="load-more-btn" 
            onClick={() => setVisibleCount(prev => prev + 20)}
            style={{
              background: 'var(--glass)',
              backdropFilter: 'blur(16px)',
              border: '1px solid var(--glass-border)',
              color: 'var(--text-main)',
              padding: '0.85rem 2.5rem',
              borderRadius: '16px',
              fontSize: '1rem',
              fontWeight: '700',
              cursor: 'pointer',
              transition: 'var(--transition)',
              boxShadow: 'var(--card-shadow)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.borderColor = 'var(--primary)';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = 'var(--glass)';
              e.currentTarget.style.borderColor = 'var(--glass-border)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            Load More Products
          </button>
        </div>
      )}
    </div>
  );
};

export default ProductGrid;
