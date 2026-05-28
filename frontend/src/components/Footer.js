import React, { useState, useEffect } from 'react';
import { getFeedback, getHealth } from '../services/api';
import './Footer.css';

const INFO_PAGES = {
  about: {
    title: 'About BuySmart',
    content: (
      <div>
        <p>BuySmart is your ultimate e-commerce search and comparison assistant. We help shoppers save time and money by aggregating real-time product options from major online marketplaces like Amazon, Flipkart, Myntra, and Meesho.</p>
        <p>Our goal is to make smart shopping accessible to everyone—from tech-savvy buyers to first-time internet users—by presenting clear, easy-to-understand product comparisons without complex terminology or clutter.</p>
      </div>
    )
  },
  faq: {
    title: 'Frequently Asked Questions',
    content: (
      <div className="info-faq-list">
        <div className="faq-item" style={{ marginBottom: '1.25rem' }}>
          <strong style={{ display: 'block', color: 'var(--text-main)', marginBottom: '0.25rem' }}>How does BuySmart work?</strong>
          <p style={{ margin: 0 }}>We fetch product details across multiple online stores in real-time, allowing you to compare price, platform, and ratings instantly in one place.</p>
        </div>
        <div className="faq-item" style={{ marginBottom: '1.25rem' }}>
          <strong style={{ display: 'block', color: 'var(--text-main)', marginBottom: '0.25rem' }}>Is BuySmart free to use?</strong>
          <p style={{ margin: 0 }}>Yes, BuySmart is 100% free to use. We do not charge any subscription fees or extra service charges.</p>
        </div>
        <div className="faq-item">
          <strong style={{ display: 'block', color: 'var(--text-main)', marginBottom: '0.25rem' }}>Can I purchase products on BuySmart?</strong>
          <p style={{ margin: 0 }}>No, we do not sell products directly. When you find a product you like, clicking 'View Deal' safely directs you to the official seller store to complete your purchase securely.</p>
        </div>
      </div>
    )
  },
  privacy: {
    title: 'Privacy Policy',
    content: (
      <div>
        <p>Your privacy is important to us. BuySmart only collects essential information needed to manage your account and personalize your wishlist and searches.</p>
        <p>We do not share, sell, or rent your personal details to third-party advertisers. All transaction and payment details are processed directly on the respective seller platforms, meaning we never store or see your financial information.</p>
      </div>
    )
  },
  terms: {
    title: 'Terms of Service',
    content: (
      <div>
        <p>By using BuySmart, you agree that all product prices, stock details, and descriptions are provided for informational purposes only. We strive to maintain accurate data, but product listings are subject to change on the merchant's website.</p>
        <p>Always verify the final price and terms on the seller's website before finalizing your purchase. BuySmart is not responsible for merchant delivery, returns, or order disputes.</p>
      </div>
    )
  },
  help: {
    title: 'Help Center',
    content: (
      <div>
        <p>Using BuySmart is simple! Follow these easy guidelines:</p>
        <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <li><strong>Search:</strong> Use the search bar at the top or on the homepage. Type keywords like "shoes under 2000" or "red shirt".</li>
          <li><strong>Filters:</strong> Narrow down results by price limit, minimum customer rating, or specific shopping platforms.</li>
          <li><strong>Wishlist:</strong> Click the heart icon (❤️) on any product to save it to your account for later viewing.</li>
          <li><strong>Price Alerts:</strong> Set price alerts to receive notifications when a product's price drops to your budget limit.</li>
        </ul>
      </div>
    )
  },
  // contact: {
  //   title: 'Contact Support',
  //   content: (
  //     <div>
  //       <p>If you have any questions, suggestions, or need assistance, our support team is ready to help you!</p>
  //       <div className="contact-details-box" style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '10px', marginTop: '1rem', border: '1px solid var(--border-color)' }}>
  //         <p style={{ margin: '0 0 0.5rem 0' }}>📧 <strong>Email Support:</strong> <a href="mailto:support@buysmart.in" style={{ color: 'var(--primary)' }}>support@buysmart.in</a></p>
  //         <p style={{ margin: '0 0 0.5rem 0' }}>📞 <strong>Toll-Free Helpline:</strong> 1800-123-4567 (Mon-Sat, 9:00 AM - 6:00 PM)</p>
  //         <p style={{ margin: 0 }}>📍 <strong>Office Address:</strong> BuySmart India Private Limited, Bangalore, Karnataka</p>
  //       </div>
  //     </div>
  //   )
  // }
};

const Footer = ({ onOpenFeedback, onNavigate }) => {
  const [feedbacks, setFeedbacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [infoKey, setInfoKey] = useState(null);
  const [healthStatus, setHealthStatus] = useState('loading');

  useEffect(() => {
    loadFeedbacks();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const data = await getHealth();
      if (data && data.status === 'healthy') {
        setHealthStatus('healthy');
      } else {
        setHealthStatus('degraded');
      }
    } catch (error) {
      console.error('Error checking health:', error);
      setHealthStatus('degraded');
    }
  };

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
    <footer className="footer" aria-label="Global Footer">
      <div className="container">
        <div className="feedback-preview-section">
          <div className="section-header">
            <h3>Hear from our users</h3>
            <button className="give-feedback-btn" onClick={onOpenFeedback} aria-label="Share your feedback">
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
              BuySmart is your ultimate shopping companion. We compare prices across major marketplaces in real-time, helping you get the best deal every time.
            </p>
          </div>

          <div className="footer-col">
            <h4>Quick Links</h4>
            <ul>
              <li><button className="footer-link-btn" onClick={() => onNavigate('home')}>Home</button></li>
              <li><button className="footer-link-btn" onClick={() => onNavigate('search')}>Search Products</button></li>
              <li><button className="footer-link-btn" onClick={() => onNavigate('dashboard')}>My Activity</button></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Support & Help</h4>
            <ul>
              <li><button className="footer-link-btn" onClick={() => setInfoKey('about')}>About Us</button></li>
              <li><button className="footer-link-btn" onClick={() => setInfoKey('faq')}>FAQs</button></li>
              <li><button className="footer-link-btn" onClick={() => setInfoKey('help')}>Help Center</button></li>
              {/* <li><button className="footer-link-btn" onClick={() => setInfoKey('contact')}>Contact Us</button></li> */}
            </ul>
          </div>

          <div className="footer-col">
            <h4>Legal</h4>
            <ul>
              <li><button className="footer-link-btn" onClick={() => setInfoKey('privacy')}>Privacy Policy</button></li>
              <li><button className="footer-link-btn" onClick={() => setInfoKey('terms')}>Terms of Service</button></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-copyright">
            Buy<span>Smart</span> © 2026. Made for Smart Shoppers.
            {healthStatus && (
              <span className={`health-status-badge ${healthStatus}`} title={`System Status: ${healthStatus}`}>
                <span className="pulse-dot"></span>
                System: {healthStatus === 'healthy' ? 'Operational' : healthStatus === 'loading' ? 'Checking...' : 'Degraded'}
              </span>
            )}
          </div>

          <div className="footer-developer">
            Developed by{' '}
            <a
              href="https://www.linkedin.com/in/jubburu-prudhvi-raju/"
              target="_blank"
              rel="noopener noreferrer"
              className="developer-link"
            >
              Jubburu Prudhvi Raju
            </a>
          </div>
        </div>
      </div>

      {/* Info Dialog Overlay Modal */}
      {infoKey && INFO_PAGES[infoKey] && (
        <div className="info-modal-overlay" onClick={() => setInfoKey(null)}>
          <div className="info-modal-card animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="info-modal-header">
              <h3>{INFO_PAGES[infoKey].title}</h3>
              <button className="info-modal-close" onClick={() => setInfoKey(null)} aria-label="Close modal">×</button>
            </div>
            <div className="info-modal-body">
              {INFO_PAGES[infoKey].content}
            </div>
            <div className="info-modal-footer">
              <button className="info-modal-close-btn" onClick={() => setInfoKey(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </footer>
  );
};

export default Footer;
