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
  searchStatus,
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
  console.log("Products passed to ProductGrid:", products);

  const getProgressPercentage = () => {
    if (!searchStatus) return 15;
    if (searchStatus.stage === 'ranking') return 90;
    if (searchStatus.stage === 'complete') return 100;
    if (searchStatus.platforms) {
      const keys = Object.keys(searchStatus.platforms);
      if (keys.length === 0) return 25;
      const completed = keys.filter(k => 
        searchStatus.platforms[k] === 'complete' || 
        searchStatus.platforms[k] === 'success' || 
        searchStatus.platforms[k] === 'failed' || 
        searchStatus.platforms[k] === 'cached'
      ).length;
      return 25 + Math.round((completed / keys.length) * 60);
    }
    return 15;
  };

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
        <div className="search-loading-container" style={{ width: '100%', marginTop: '2rem' }}>
          <div className="progress-card" style={{
            background: 'var(--glass)',
            backdropFilter: 'blur(16px)',
            border: '1px solid var(--glass-border)',
            borderRadius: '24px',
            padding: '2rem',
            marginBottom: '2rem',
            boxShadow: 'var(--card-shadow)'
          }}>
            <h3 style={{ marginBottom: '1.5rem', color: 'var(--text-main)', fontSize: '1.2rem', fontWeight: '700' }}>Live Search Progress</h3>
            
            {/* Animated progress bar */}
            <div className="progress-bar-container" style={{
              width: '100%',
              height: '8px',
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '4px',
              overflow: 'hidden',
              marginBottom: '2rem',
              position: 'relative'
            }}>
              <div className="progress-bar-fill" style={{
                height: '100%',
                background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
                width: `${getProgressPercentage()}%`,
                transition: 'width 0.4s ease'
              }} />
            </div>

            {/* Platform checklists */}
            <div className="platform-statuses" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem'
            }}>
              {Object.keys(searchStatus?.platforms || { amazon: 'pending', flipkart: 'pending', myntra: 'pending', meesho: 'pending' }).map((p) => {
                const status = searchStatus?.platforms?.[p] || 'pending';
                const label = p.charAt(0).toUpperCase() + p.slice(1);
                
                let icon = '⏳';
                let color = 'var(--text-dim)';
                let text = `Searching ${label}...`;
                
                if (status === 'complete' || status === 'success') {
                  icon = '✓';
                  color = '#10b981';
                  text = `${label} Complete`;
                } else if (status === 'failed') {
                  icon = '✕';
                  color = '#ef4444';
                  text = `${label} Failed`;
                } else if (status === 'searching') {
                  icon = '🔄';
                  color = 'var(--primary)';
                  text = `Searching ${label}...`;
                } else if (status === 'cached') {
                  icon = '📦';
                  color = '#3b82f6';
                  text = `${label} Cached`;
                } else {
                  text = `Pending ${label}`;
                }

                return (
                  <div key={p} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem 1rem',
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.05)',
                    color: color,
                    fontWeight: '600',
                    fontSize: '0.95rem'
                  }}>
                    <span style={{ fontSize: '1.2rem' }}>{icon}</span>
                    <span>{text}</span>
                  </div>
                );
              })}
            </div>
            
            <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.9rem', fontWeight: '500' }}>
              {searchStatus?.stage === 'ranking' ? (
                <span className="stage-ranking-pulse">Ranking and sorting products...</span>
              ) : (
                <span>Scanning multiple online marketplaces in real-time...</span>
              )}
            </div>
          </div>
          
          <div className="product-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '2rem', opacity: 0.4, pointerEvents: 'none' }}>
            {Array.from({ length: 8 }).map((_, i) => (
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
            platformStatus={searchResult && searchResult.platform_status}
          />
        </>
      )}
    </main>
  );
};

export default SearchPage;
