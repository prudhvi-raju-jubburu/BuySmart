import React from 'react';
import './SkeletonCard.css';

export const SkeletonCard = ({ style }) => {
  return (
    <div className="skeleton-card" style={style}>
      <div className="skeleton-img"></div>
      <div className="skeleton-text-content">
        <div className="skeleton-line skeleton-title"></div>
        <div className="skeleton-line skeleton-subtitle"></div>
        <div className="skeleton-line skeleton-price"></div>
      </div>
    </div>
  );
};

export const SkeletonStat = () => {
  return (
    <div className="skeleton-stat">
      <div className="skeleton-stat-title"></div>
      <div className="skeleton-stat-value"></div>
    </div>
  );
};

export const SkeletonRow = () => {
  return (
    <div className="skeleton-row"></div>
  );
};

export const SkeletonTable = () => {
  return (
    <div className="skeleton-table">
      {[...Array(5)].map((_, i) => (
        <div className="skeleton-table-row" key={i}>
          <div className="skeleton-table-cell short"></div>
          <div className="skeleton-table-cell medium"></div>
          <div className="skeleton-table-cell long"></div>
        </div>
      ))}
    </div>
  );
};

export const SkeletonProfile = () => {
  return (
    <div className="skeleton-profile">
      <div className="skeleton-avatar"></div>
      <div className="skeleton-line skeleton-name"></div>
      <div className="skeleton-line skeleton-email"></div>
      <div className="skeleton-profile-fields">
        <div className="skeleton-field"></div>
        <div className="skeleton-field"></div>
      </div>
    </div>
  );
};

export const SkeletonDashboard = () => {
  return (
    <div className="skeleton-dashboard">
      <div className="skeleton-stats-grid">
        {[...Array(4)].map((_, i) => (
          <SkeletonStat key={i} />
        ))}
      </div>
      <div className="skeleton-dashboard-main">
        <SkeletonRow />
        <SkeletonRow />
      </div>
    </div>
  );
};
