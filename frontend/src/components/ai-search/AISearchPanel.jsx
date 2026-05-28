import React, { useState } from 'react';
import './AISearch.css';
import AISearchBar from './AISearchBar';
import IntentSummary from './IntentSummary';
import SearchExplanation from './SearchExplanation';
import SuggestedQueries from './SuggestedQueries';
import AISearchResults from './AISearchResults';
import { searchProductsAI, submitAISearchFeedback } from '../../services/api';

const AISearchPanel = ({ user }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  
  // Selection/comparison state (optional)
  const [selectedProducts, setSelectedProducts] = useState([]);

  const handleSearch = async (searchQuery) => {
    setIsLoading(true);
    setError("");
    setQuery(searchQuery);
    setSelectedProducts([]);
    
    try {
      const data = await searchProductsAI(searchQuery);
      if (data.success) {
        setResult(data);
      } else {
        setError(data.message || "Could not retrieve search results.");
      }
    } catch (err) {
      console.error("AI Search Error:", err);
      setError(err?.response?.data?.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSelect = (product) => {
    setSelectedProducts((prev) => {
      const exists = prev.some((p) => p.id === product.id);
      if (exists) {
        return prev.filter((p) => p.id !== product.id);
      }
      if (prev.length >= 3) {
        window.showToast?.("You can compare a maximum of 3 products.", "warning");
        return prev;
      }
      return [...prev, product];
    });
  };

  return (
    <div className="ai-search-container">
      {/* Search Box */}
      <AISearchBar 
        onSearch={handleSearch} 
        isLoading={isLoading} 
        initialQuery={query}
      />

      {/* Error state */}
      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '2rem',
          textAlign: 'center'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Loading state spinner */}
      {isLoading && (
        <div className="ai-loader-container glass-card">
          <div className="glowing-circle"></div>
          <span className="loading-text">
            Searching for the best products across stores...
          </span>
          <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.5)', margin: 0 }}>
            Analyzing prices, checking stock, and compiling direct recommendations...
          </p>
        </div>
      )}

      {/* Results panel */}
      {!isLoading && result && (
        <>
          {/* Query refinements list */}
          {result.suggested_queries && result.suggested_queries.length > 0 && (
            <SuggestedQueries 
              queries={result.suggested_queries} 
              onSelectQuery={handleSearch} 
            />
          )}

          {/* Extracted Intent and Explanations Info Box */}
          <div className="ai-info-grid">
            <IntentSummary 
              intent={result.intent} 
              confidence={result.confidence}
            />
            
            <SearchExplanation 
              eventId={result.event_id}
              bullets={result.intent?.search_explanation_bullets}
              initialExplanation={result.search_explanation}
              onSubmitFeedback={submitAISearchFeedback}
            />
          </div>

          {/* Results Grid */}
          <AISearchResults 
            products={result.products} 
            searchQuery={query}
            user={user}
            selectedProducts={selectedProducts}
            onToggleSelect={handleToggleSelect}
          />
        </>
      )}
    </div>
  );
};

export default AISearchPanel;
