import React from 'react';
import ProductCard from './ProductCard';
import './ProductGrid.css';

const ProductGrid = ({ products, searchQuery, user, selectedProducts, onToggleSelect, isAi, platformStatus }) => {
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
    
    if (hasFailures) {
      return (
        <div className="no-results">
          <h2>🔍 No products found</h2>
          <p>Some stores are temporarily unavailable. No matching products were found on the available stores.</p>
          <p style={{ marginTop: '1.5rem', opacity: 0.7 }}>Or try searching with different keywords or removing some filters.</p>
        </div>
      );
    }

    return (
      <div className="no-results">
        <h2>🔍 No products found</h2>
        <p>No matching products were found for your search.</p>
        <p style={{ marginTop: '1.5rem', opacity: 0.7 }}>Or try searching with different keywords or removing some filters.</p>
      </div>
    );
  }


  if (products.length === 0) {
    return (
      <div className="no-results" style={{ marginTop: '2rem' }}>
        <h2>👆 Ready to shop?</h2>
        <p>Type what you want to buy in the search box above to find the best deals.</p>
      </div>
    );
  }

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
      <div className="results-count">
        {isAi ? (
          <span>✨ Suggested For You ({products.length} found)</span>
        ) : (
          <span>☀️ Showing Top {products.length} Best Products for You</span>
        )}
      </div>
      <div className="product-grid">
        {products.map((product) => {
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
    </div>
  );
};

export default ProductGrid;
