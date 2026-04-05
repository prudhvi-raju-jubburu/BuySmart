import React, { useState, useEffect } from 'react';
import { getFeedback } from '../services/api';
import './Footer.css';

const Footer = ({ onOpenFeedback, onNavigate }) => {
  const [feedbacks, setFeedbacks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFeedbacks();
  }, []);

  const loadFeedbacks = async () => {
    try {
      const data = await getFeedback({ limit: 4, min_stars: 4 });
      setFeedbacks(data.items || []);
    } catch (error) {
      console.error('Error loading feedbacks:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (rating) => {
    return '★'.repeat(rating) + '☆'.repeat(5 - rating);
  };

  return (
    <footer className="footer">
      <div className="container">
        <div className="feedback-preview-section">
          <div className="section-header">
            <h3>Hear from our users</h3>
            <button className="give-feedback-btn" onClick={onOpenFeedback}>
              Share your experience
            </button>
          </div>
          
          <div className="feedback-grid">
            {loading ? (
              <div className="loading-feedbacks">Loading reviews...</div>
            ) : feedbacks.length > 0 ? (
              feedbacks.map((f) => (
                <div key={f.id} className="feedback-card">
                  <div className="feedback-stars">{renderStars(f.rating)}</div>
                  <p className="feedback-desc">"{f.description}"</p>
                  <div className="feedback-author">
                    <div className="author-avatar">{f.name?.[0] || 'A'}</div>
                    <span>{f.name}</span>
                  </div>
                </div>
              ))
            ) : (
                <div className="no-feedbacks">Be the first to leave a review!</div>
            )}
          </div>
        </div>

        <div className="footer-main-grid">
          <div className="footer-col about-col">
            <div className="footer-logo">
              Buy<span>Smart</span>
            </div>
            <p className="footer-about-text">
              BuySmart is your ultimate companion for smart shopping. We compare prices across major e-commerce platforms in real-time to ensure you always get the best deal.
            </p>
            <div className="social-links">
              <a href="#" className="social-icon">fb</a>
              <a href="#" className="social-icon">tw</a>
              <a href="#" className="social-icon">ig</a>
              <a href="#" className="social-icon">in</a>
            </div>
          </div>

          <div className="footer-col">
            <h4>Quick Links</h4>
            <ul>
              <li><a onClick={() => onNavigate('trending')}>Top Deals</a></li>
              <li><a onClick={() => onNavigate('search')}>Price History</a></li>
              <li><a onClick={() => onNavigate('search')}>Comparative Search</a></li>
              <li><a onClick={() => onNavigate('analytics')}>Smart Analytics</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Categories</h4>
            <ul>
              <li><a onClick={() => onNavigate('search', 'electronics')}>Electronics</a></li>
              <li><a onClick={() => onNavigate('search', 'fashion')}>Fashion</a></li>
              <li><a onClick={() => onNavigate('search', 'mobiles')}>Mobiles</a></li>
              <li><a onClick={() => onNavigate('search', 'laptops')}>Laptops</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Help & Support</h4>
            <ul>
              <li><a onClick={() => onNavigate('home')}>About Us</a></li>
              <li><a onClick={() => alert('FAQ section coming soon!')}>FAQs</a></li>
              <li><a onClick={() => alert('Policy updated: 2026')}>Privacy Policy</a></li>
              <li><a onClick={() => alert('Terms updated: 2026')}>Terms & Conditions</a></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-copyright">
            Buy<span>Smart</span> © 2026. Made for Smart Shoppers.
          </div>
          <div className="footer-extra-links">
            <a href="#">Sitemap</a>
            <a href="#">Security</a>
            <a href="#">Contact Us</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
