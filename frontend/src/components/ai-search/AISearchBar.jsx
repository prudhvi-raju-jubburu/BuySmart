import React, { useState, useRef, useEffect } from 'react';

const AISearchBar = ({ onSearch, isLoading, initialQuery = "" }) => {
  const [query, setQuery] = useState(initialQuery);
  const textareaRef = useRef(null);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  // Auto-resize textarea to fit text
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [query]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter, unless Shift is pressed
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="search-bar-wrapper glass-card">
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.5rem', fontWeight: '700', color: '#818cf8' }}>
        AI-Powered Natural Language Search 🤖
      </h2>
      <p style={{ margin: '0 0 1.5rem 0', color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.95rem' }}>
        Type anything you want in plain English (e.g. <em>"Need a Lenovo laptop for coding under 60k with 16GB RAM"</em> or <em>"Looking for a premium Nike running shoe around 8000"</em>).
      </p>
      
      <form onSubmit={handleSubmit}>
        <div className="search-input-container">
          <textarea
            ref={textareaRef}
            className="ai-textarea"
            placeholder="What products are you looking for today? Describe your requirements, budget, or brand preferences..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          <button 
            type="submit" 
            className="search-submit-btn"
            disabled={isLoading || !query.trim()}
          >
            {isLoading ? (
              <>
                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                Analyzing...
              </>
            ) : (
              <>
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Search
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AISearchBar;
