import React, { useEffect, useState } from 'react';
import './TrendingSection.css';
import { getTrendingProducts } from '../services/api';
import ProductCard from './ProductCard';

const TrendingSection = ({ user }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getTrendingProducts({ days: 7, limit: 8 });
      setItems(data.items || []);
    } catch (_e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="trending">
      <div className="trending-header">
        <div className="trending-title">Trending Products (based on clicks)</div>
        <button className="trending-refresh" onClick={load} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      <div className="trending-grid">
        {items.length === 0 ? (
          <div className="trending-empty">
            No trending data yet. Search a product and click <b>Buy Now</b> to generate trending activity.
          </div>
        ) : (
          items.map((p) => <ProductCard key={`tr-${p.id}`} product={p} user={user} source="trending" />)
        )}
      </div>
    </div>
  );
};

export default TrendingSection;


