import React, { useState } from 'react';
import ProductCard from '../ProductCard';

const AISearchResults = ({ products, searchQuery, user, selectedProducts, onToggleSelect }) => {
  if (!products || products.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '1.1rem' }}>
          No matching products found. Try refining your request.
        </p>
      </div>
    );
  }

  return (
    <div style={{ marginTop: '2rem' }}>
      <h3 className="results-grid-header">
        ✨ Best Matches for You ({products.length} found)
      </h3>
      
      <div className="product-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1.5rem', marginTop: '1rem' }}>
        {products.map((product) => {
          return (
            <div key={product.id} style={{ position: 'relative' }}>
              <ProductCard
                product={product}
                user={user}
                source="ai-search"
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

export default AISearchResults;
