import React, { useState, useEffect } from 'react';
import { getRecommendations } from '../services/api';
import ProductCard from './ProductCard';
import './Recommendations.css';

const Recommendations = ({ user }) => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const data = await getRecommendations({ limit: 20 });
      setRecommendations(data.items || []);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="recommendations-skeleton">
        <h2 className="section-title">Top Rated Recommendations</h2>
        <div className="skeleton-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton-card"></div>
          ))}
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) return null;

  return (
    <section className="recommendations-section">
      <div className="section-header">
        <h2 className="section-title">Top Picks for You</h2>
        <p className="section-subtitle">Based on performance, ratings, and best price value across platforms.</p>
      </div>
      
      <div className="recommendations-grid">
        {recommendations.map(product => (
          <ProductCard 
            key={product.id} 
            product={product} 
            user={user} 
            source="recommendation"
          />
        ))}
      </div>
    </section>
  );
};

export default Recommendations;
