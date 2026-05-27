import React, { useState, useEffect, useCallback } from 'react';
import { getDashboardSearchHistory, deleteSearchHistoryEntry } from '../../services/api';
import { SkeletonTable } from '../SkeletonCard';

const SearchHistoryPanel = () => {
  const [historyItems, setHistoryItems] = useState([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [mostSearchedCategory, setMostSearchedCategory] = useState(null);
  const [frequentTerms, setFrequentTerms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardSearchHistory({
        page,
        per_page: 8,
        query: searchFilter
      });
      if (res.success) {
        setHistoryItems(res.data.items);
        setTotalPages(res.data.pages);
        setTotalCount(res.data.total);
        setMostSearchedCategory(res.data.most_searched_category);
        setFrequentTerms(res.data.frequent_search_terms || []);
      } else {
        setError(res.message || 'Failed to fetch search history');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error fetching search history');
    } finally {
      setLoading(false);
    }
  }, [page, searchFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleFilterChange = (e) => {
    setSearchFilter(e.target.value);
    setPage(1); // Reset to first page when filtering
  };

  const handleDeleteEntry = async (eventId) => {
    if (!window.confirm('Are you sure you want to remove this search query from your history?')) {
      return;
    }
    try {
      const res = await deleteSearchHistoryEntry(eventId);
      if (res.success) {
        // Fetch history again to keep pagination count aligned
        fetchHistory();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Error deleting search history entry');
    }
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    return new Date(isoStr).toLocaleString();
  };

  return (
    <div className="search-history-panel animate-fade-in">
      {/* Search Intelligence Cards */}
      <div className="search-intel-grid">
        <div className="intel-card purple">
          <div className="intel-icon">🏷️</div>
          <div className="intel-info">
            <span className="intel-value">{mostSearchedCategory || 'None Yet'}</span>
            <span className="intel-label">Most Searched Category</span>
          </div>
        </div>

        <div className="intel-card teal">
          <div className="intel-icon">🔥</div>
          <div className="intel-info">
            <div className="frequent-tags">
              {frequentTerms.length > 0 ? (
                frequentTerms.map((item, idx) => (
                  <span key={idx} className="freq-tag" title={`${item.count} searches`}>
                    {item.term} <span className="tag-count">({item.count})</span>
                  </span>
                ))
              ) : (
                <span className="no-tags">No searches yet</span>
              )}
            </div>
            <span className="intel-label">Most Frequent Search Terms</span>
          </div>
        </div>
      </div>

      {/* Filter and List Section */}
      <div className="history-list-card">
        <div className="panel-header">
          <h3 className="card-title">Search History List</h3>
          <div className="filter-wrapper">
            <input
              type="text"
              value={searchFilter}
              onChange={handleFilterChange}
              placeholder="Search previous queries..."
              className="search-history-filter"
            />
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        {loading ? (
          <div style={{ padding: '1rem 0' }}>
            <SkeletonTable />
          </div>
        ) : (
          <>
            <div className="history-table-wrapper">
              {historyItems.length > 0 ? (
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Search Query</th>
                      <th>Date & Time</th>
                      <th>Results Count</th>
                      <th style={{ textAlign: 'center' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyItems.map((item) => (
                      <tr key={item.id}>
                        <td className="query-text bold">{item.query}</td>
                        <td className="query-date">{formatDate(item.created_at)}</td>
                        <td className="query-results">{item.results_count} products</td>
                        <td style={{ textAlign: 'center' }}>
                          <button
                            onClick={() => handleDeleteEntry(item.id)}
                            className="delete-history-btn"
                            title="Delete entry"
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4rem 2rem', color: 'var(--text-dim)' }}>
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '1rem', color: 'var(--primary)' }}>
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  <h4 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>You haven't searched anything yet.</h4>
                  <p style={{ textAlign: 'center', maxWidth: '300px' }}>Try searching for laptops, mobiles, or fashion products.</p>
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="pagination-controls">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
                  className="page-btn"
                >
                  Previous
                </button>
                <span className="page-info">
                  Page <strong className="bold">{page}</strong> of <strong className="bold">{totalPages}</strong> ({totalCount} searches)
                </span>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
                  className="page-btn"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default SearchHistoryPanel;
