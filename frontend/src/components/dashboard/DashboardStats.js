import React from 'react';
import { SkeletonStat } from '../SkeletonCard';

const DashboardStats = ({ stats, loading }) => {
  if (loading || !stats) {
    return (
      <div className="dashboard-stats-grid">
        {[...Array(6)].map((_, idx) => (
          <SkeletonStat key={idx} />
        ))}
      </div>
    );
  }

  const cardItems = [
    {
      title: 'Total Searches',
      value: stats.total_searches,
      icon: '🔍',
      colorClass: 'blue',
      description: 'Total search requests submitted'
    },
    {
      title: 'Product Views',
      value: stats.product_views,
      icon: '👀',
      colorClass: 'purple',
      description: 'Products viewed on retail sites'
    },
    {
      title: 'Wishlist Items',
      value: stats.wishlist_items,
      icon: '❤️',
      colorClass: 'pink',
      description: 'Products saved for later'
    },
    {
      title: 'Active Alerts',
      value: stats.active_price_alerts,
      icon: '🔔',
      colorClass: 'yellow',
      description: 'Active price drop monitors'
    },
    {
      title: 'Recommendation Clicks',
      value: `${stats.recommendation_clicks} (${(stats.recommendation_ctr * 100).toFixed(1)}% CTR)`,
      icon: '✨',
      colorClass: 'teal',
      description: 'Engagement with AI matches'
    },
    {
      title: 'Total Purchases',
      value: stats.total_purchases,
      icon: '🛍️',
      colorClass: 'green',
      description: 'Simulated products bought'
    }
  ];

  return (
    <div className="dashboard-stats-grid">
      {cardItems.map((item, idx) => (
        <div key={idx} className={`stat-card ${item.colorClass}`}>
          <div className="stat-card-header">
            <span className="stat-card-icon">{item.icon}</span>
            <span className="stat-card-title">{item.title}</span>
          </div>
          <div className="stat-card-body">
            <span className="stat-card-value">{item.value}</span>
            <span className="stat-card-desc">{item.description}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DashboardStats;
