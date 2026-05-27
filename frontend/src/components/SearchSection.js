import React, { useState, useEffect } from 'react';
import './SearchSection.css';

const SearchSection = ({ onSearch, filters: initialFilters, onClearFilters, onClearHistory, history = [], user }) => {
  const [query, setQuery] = useState('');
  const [localFilters, setLocalFilters] = useState(initialFilters);

  useEffect(() => {
    setLocalFilters(initialFilters);
  }, [initialFilters]);

  // ... (handle functions remain same)

  const handleFilterChange = (key, value) => {
    setLocalFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handlePlatformToggle = (platform) => {
    setLocalFilters(prev => {
      const platforms = prev.platforms.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...prev.platforms, platform];
      return { ...prev, platforms };
    });
  };

  const handleQuickFilter = (type) => {
    setLocalFilters(prev => {
      let updates = {};
      if (type === 'under10k') {
        updates = { maxPrice: prev.maxPrice === '10000' ? '' : '10000' };
      } else if (type === 'under50k') {
        updates = { maxPrice: prev.maxPrice === '50000' ? '' : '50000' };
      } else if (type === 'fourStars') {
        updates = { minRating: prev.minRating === '4' ? '' : '4' };
      } else if (type === 'fastMode') {
        updates = { fastMode: !prev.fastMode };
      }
      return { ...prev, ...updates };
    });
  };

  const [isListening, setIsListening] = useState(false);

  const handleVoiceSearch = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition. Please try Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      setIsListening(false);
    };

    recognition.onerror = (e) => {
      console.error(e.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query, localFilters);
  };

  return (
    <div className="search-section">
      <form onSubmit={handleSubmit}>
        <div className="search-box">
          <div className="input-group">
            <input
              type="text"
              className="search-input"
              placeholder="Search products..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button 
              type="button" 
              className={`voice-btn ${isListening ? 'listening' : ''}`}
              onClick={handleVoiceSearch}
              title="Voice Search"
            >
              <div className="mic-icon-wrapper">
                {isListening ? (
                  <span className="mic-status-dot"></span>
                ) : (
                  <span className="mic-symbol">🎙️</span>
                )}
              </div>
            </button>
          </div>
          <button type="submit" className="search-btn">
            Compare
          </button>
        </div>

        <div className="filters">
          <div className="filter-row">
            <div className="filter-group">
              <label className="filter-label">Price Range (₹):</label>
              <input
                type="number"
                placeholder="Min"
                className="filter-input"
                value={localFilters.minPrice}
                onChange={(e) => handleFilterChange('minPrice', e.target.value)}
              />
              <span style={{ color: 'var(--text-dim)' }}>-</span>
              <input
                type="number"
                placeholder="Max"
                className="filter-input"
                value={localFilters.maxPrice}
                onChange={(e) => handleFilterChange('maxPrice', e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">Min Rating:</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="5"
                placeholder="4.0"
                className="filter-input"
                value={localFilters.minRating}
                onChange={(e) => handleFilterChange('minRating', e.target.value)}
              />
            </div>

            <button
              type="button"
              className="clear-filters-btn"
              onClick={onClearFilters}
            >
              Clear Filters
            </button>
          </div>

          <div className="filter-row chips-row">
            <div className="filter-group platforms-group">
              <label className="filter-label">Stores:</label>
              <div className="filter-chips-container">
                {['Amazon', 'Flipkart', 'Myntra', 'Meesho'].map(p => (
                  <button
                    type="button"
                    key={p}
                    className={`filter-chip ${localFilters.platforms.includes(p) ? 'active' : ''}`}
                    onClick={() => handlePlatformToggle(p)}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-group quick-filters-group">
              <label className="filter-label">Quick Filters:</label>
              <div className="filter-chips-container">
                <button
                  type="button"
                  className={`filter-chip preset ${localFilters.maxPrice === '10000' ? 'active' : ''}`}
                  onClick={() => handleQuickFilter('under10k')}
                >
                  Under ₹10,000
                </button>
                <button
                  type="button"
                  className={`filter-chip preset ${localFilters.maxPrice === '50000' ? 'active' : ''}`}
                  onClick={() => handleQuickFilter('under50k')}
                >
                  Under ₹50,000
                </button>
                <button
                  type="button"
                  className={`filter-chip preset ${localFilters.minRating === '4' ? 'active' : ''}`}
                  onClick={() => handleQuickFilter('fourStars')}
                >
                  4★ & Above
                </button>
                <button
                  type="button"
                  className={`filter-chip preset ${localFilters.fastMode ? 'active' : ''}`}
                  onClick={() => handleQuickFilter('fastMode')}
                >
                  ⚡ Fast Search
                </button>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default SearchSection;
