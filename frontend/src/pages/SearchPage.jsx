import React from 'react';
import SearchSection from '../components/SearchSection';
import '../components/ai-search/AISearch.css';
import SuggestedQueries from '../components/ai-search/SuggestedQueries';
import IntentSummary from '../components/ai-search/IntentSummary';
import SearchExplanation from '../components/ai-search/SearchExplanation';
import ProductGrid from '../components/ProductGrid';
import { SkeletonCard } from '../components/SkeletonCard';

const SearchPage = ({
  user,
  loading,
  products,
  searchQuery,
  searchResult,
  filters,
  selectedProducts,
  onSearch,
  onClearFilters,
  onToggleSelect,
  onSubmitAISearchFeedback
}) => {
  return (
    <main className="container main-content">
      {/* Standardized Page Header */}
      <div className="page-header-card">
        <h2 className="page-title">Search</h2>
        <p className="page-subtitle">Search and compare products from multiple stores.</p>
      </div>

      <SearchSection
        onSearch={onSearch}
        filters={filters}
        onClearFilters={onClearFilters}
        user={user}
      />
      {loading ? (
        <div className="skeleton-grid-container" style={{ width: '100%', marginTop: '2rem' }}>
          <div className="results-count" style={{ marginBottom: '1.5rem', color: 'var(--text-dim)', fontSize: '0.9rem', fontWeight: '600' }}>
            <span>Finding the best deals for you...</span>
          </div>
          <div className="product-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '2rem' }}>
            {[...Array(8)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      ) : (
        <>
          {searchResult && searchResult.is_ai && (
            <div className="ai-search-details-merged" style={{ marginBottom: '2rem', width: '100%' }}>
              {searchResult.suggested_queries && searchResult.suggested_queries.length > 0 && (
                <SuggestedQueries
                  queries={searchResult.suggested_queries}
                  onSelectQuery={(q) => onSearch(q, filters)}
                />
              )}
              <div className="ai-info-grid">
                <IntentSummary
                  intent={searchResult.intent}
                  confidence={searchResult.confidence}
                />
                <SearchExplanation
                  eventId={searchResult.event_id}
                  bullets={searchResult.intent?.search_explanation_bullets}
                  initialExplanation={searchResult.search_explanation}
                  onSubmitFeedback={onSubmitAISearchFeedback}
                />
              </div>
            </div>
          )}

          <ProductGrid
            products={products}
            searchQuery={searchQuery}
            user={user}
            selectedProducts={selectedProducts}
            onToggleSelect={onToggleSelect}
            isAi={searchResult && searchResult.is_ai}
          />
        </>
      )}
    </main>
  );
};

export default SearchPage;
