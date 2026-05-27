import React, { useEffect, useState } from 'react';
import { getDashboardRecentlyViewed } from '../../services/api';
import ProductCard from '../ProductCard';
import { SkeletonCard } from '../SkeletonCard';

const RecentlyViewedPanel = ({ user }) => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRecentlyViewed = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardRecentlyViewed();
      if (res.success) {
        setProducts(res.data || []);
      } else {
        setError(res.message || 'Failed to load recently viewed products');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error loading recently viewed products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentlyViewed();
  }, []);

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    return new Date(isoStr).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="recently-viewed-panel animate-fade-in">
      <div className="panel-header">
        <h3 className="card-title">Recently Viewed Products</h3>
        <span className="subtitle-desc">Your last 20 unique product views</span>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="recent-products-grid">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : products.length > 0 ? (
        <div className="recent-products-grid">
          {products.map((product) => (
            <div key={product.id} className="recent-product-wrapper">
              <div className="viewed-timestamp">
                👁️ Viewed {formatDate(product.viewed_at)}
              </div>
              <ProductCard
                product={product}
                user={user}
                source="recently_viewed"
                isSelected={false}
                onToggleSelect={() => {}} // Disabled comparison inside recently viewed to keep UX simple
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">👀</div>
          <h4>No Recently Viewed Products</h4>
          <p>Products you click while searching will show up here so you can easily find them later.</p>
        </div>
      )}
    </div>
  );
};

export default RecentlyViewedPanel;
