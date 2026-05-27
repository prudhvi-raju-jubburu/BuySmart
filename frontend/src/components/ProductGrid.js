import React from 'react';
import ProductCard from './ProductCard';
import './ProductGrid.css';

const ProductGrid = ({ products, searchQuery, user, selectedProducts, onToggleSelect, isAi }) => {
  if (products.length === 0 && searchQuery) {
    return (
      <div className="no-results">
        <h2>🔍 No products found for "{searchQuery}"</h2>
        <p>This could be because our system is currently scanning the platforms for you.</p>
        <div className="alert-info" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px' }}>
          <p>💡 <strong>Tip:</strong> If this is your first time here, our backend might be bootstrapping initial deals in the background! Try again in 2 minutes.</p>
        </div>
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
