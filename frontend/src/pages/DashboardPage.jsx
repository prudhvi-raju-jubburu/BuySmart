import React, { useState, useEffect } from 'react';
import SearchHistoryPanel from '../components/dashboard/SearchHistoryPanel';
import RecentlyViewedPanel from '../components/dashboard/RecentlyViewedPanel';
import WishlistPanel from '../components/dashboard/WishlistPanel';
import PriceAlertPanel from '../components/dashboard/PriceAlertPanel';
import { SkeletonDashboard } from '../components/SkeletonCard';
import '../components/dashboard/UserDashboard.css';

const DashboardPage = ({ user, onNavigate }) => {
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPageLoading(false);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="dashboard-page">
      <div className="dashboard-inner">
        {/* Back button */}
        <button className="dashboard-back-btn" onClick={() => onNavigate?.('search')} aria-label="Back to search">
          ← Back to Search
        </button>

        {/* Standardized Page Header */}
        <div className="page-header-card">
          <h2 className="page-title">My Activity</h2>
          <p className="page-subtitle">
            View saved products, searches, and alerts.
          </p>
        </div>


        {/* Vertical sections stack or Skeleton */}
        {pageLoading ? (
          <SkeletonDashboard />
        ) : (
          <div className="dashboard-sections-stack">
            {/* Wishlist Panel */}
            <div className="dashboard-section-card" id="wishlist-section">
              <WishlistPanel user={user} />
            </div>

            {/* Price Alerts Panel */}
            <div className="dashboard-section-card" id="price-alerts-section">
              <PriceAlertPanel />
            </div>

            {/* Recently Viewed Panel */}
            <div className="dashboard-section-card" id="recently-viewed-section">
              <RecentlyViewedPanel user={user} />
            </div>

            {/* Search History Panel */}
            <div className="dashboard-section-card" id="search-history-section">
              <SearchHistoryPanel />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
