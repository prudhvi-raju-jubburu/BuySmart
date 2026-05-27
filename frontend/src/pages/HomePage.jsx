import React, { useState } from 'react';
import HomePlatforms from '../components/HomePlatforms';
import Recommendations from '../components/Recommendations';
import './HomePage.css';

const HomePage = ({ user, onSearch, filters }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch?.(query, filters || {
        minPrice: '',
        maxPrice: '',
        platforms: ['Amazon', 'Flipkart', 'Meesho', 'Myntra'],
        minRating: '',
        fastMode: true,
        includeLiveScraping: true
      });
    }
  };

  const handleSuggestionClick = (suggestion) => {
    onSearch?.(suggestion, filters || {
      minPrice: '',
      maxPrice: '',
      platforms: ['Amazon', 'Flipkart', 'Meesho', 'Myntra'],
      minRating: '',
      fastMode: true,
      includeLiveScraping: true
    });
  };

  const suggestions = [
    "Laptop under ₹50,000",
    "Best running shoes",
    "Phone with good camera",
    "Bluetooth headphones"
  ];

  return (
    <div className="home-page-container">
      {/* Hero Section */}
      <section className="home-hero-section">
        <div className="container hero-inner">
          <h1 className="home-hero-logo">BuySmart</h1>
          <h1 className="hero-title">Find the Best Products at the Best Prices</h1>
          <p className="hero-subtitle">
            Compare products across multiple shopping platforms and discover better deals instantly.
          </p>

          {/* Hero Search Box */}
          <form onSubmit={handleSubmit} className="hero-search-form">
            <div className="hero-search-box">
              <input
                type="text"
                className="hero-search-input"
                placeholder="Search products (e.g. 'Laptop', 'Running shoes')..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search products"
              />
              <button type="submit" className="hero-search-btn" aria-label="Search Button">
                Search
              </button>
            </div>
          </form>

          {/* Quick Suggestions */}
          <div className="hero-suggestions">
            <span className="suggestions-label">Try searching for:</span>
            <div className="suggestions-buttons">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="suggestion-tag-btn"
                  onClick={() => handleSuggestionClick(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <div className="container tab-content">
        <HomePlatforms />
        <Recommendations user={user} />
      </div>
    </div>
  );
};

export default HomePage;
