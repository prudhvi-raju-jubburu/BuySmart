import React, { useEffect, useState } from 'react';
import { getDashboardActivityAnalytics } from '../../services/api';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
  PieChart, Pie, Legend
} from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#14b8a6', '#10b981', '#ef4444'];

const ActivityAnalytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardActivityAnalytics();
      if (res.success) {
        setData(res.data);
      } else {
        setError(res.message || 'Failed to load activity analytics');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error loading activity analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const formatActivityTime = (isoStr) => {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    const now = new Date();
    
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
      if (diffHrs === 0) {
        const diffMins = Math.floor(diffMs / (1000 * 60));
        return diffMins <= 1 ? 'Just now' : `${diffMins} minutes ago`;
      }
      return `${diffHrs} hours ago`;
    } else if (diffDays === 1) {
      return 'Yesterday';
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const getTimelineIcon = (type) => {
    switch (type) {
      case 'view': return '👀';
      case 'wishlist': return '❤️';
      case 'alert': return '🔔';
      case 'purchase': return '🛍️';
      default: return '📝';
    }
  };

  if (loading) {
    return (
      <div className="panel-loading">
        <div className="spinner"></div>
        <span>Loading analytics insights...</span>
      </div>
    );
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!data) return null;

  return (
    <div className="activity-analytics-container animate-fade-in">
      <div className="panel-header">
        <h3 className="card-title">Activity & Personal Analytics</h3>
        <span className="subtitle-desc">Visual insights of your shopping journey and retail engagement</span>
      </div>

      {/* Numerical Metrics Summary Bar */}
      <div className="analytics-metrics-grid">
        <div className="metric-box blue">
          <span className="metric-val">{data.searches_week}</span>
          <span className="metric-lbl">Searches This Week</span>
        </div>
        <div className="metric-box purple">
          <span className="metric-val">{data.searches_month}</span>
          <span className="metric-lbl">Searches This Month</span>
        </div>
        <div className="metric-box pink">
          <span className="metric-val text-truncate" title={data.most_viewed_category}>{data.most_viewed_category || 'N/A'}</span>
          <span className="metric-lbl">Most Viewed Category</span>
        </div>
        <div className="metric-box yellow">
          <span className="metric-val">{data.most_clicked_platform || 'N/A'}</span>
          <span className="metric-lbl">Most Clicked Platform</span>
        </div>
        <div className="metric-box teal">
          <span className="metric-val">{data.most_active_day || 'N/A'}</span>
          <span className="metric-lbl">Most Active Day</span>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="analytics-charts-grid">
        {/* Search Trend Chart */}
        <div className="chart-wrapper area-chart-wrap">
          <h4 className="chart-title">Search Trend (Last 14 Days)</h4>
          <div className="chart-container-inner">
            {data.search_trend && data.search_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={data.search_trend}>
                  <defs>
                    <linearGradient id="colorSearches" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(20, 20, 25, 0.95)',
                      border: '1px solid var(--glass-border)',
                      borderRadius: '12px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                    itemStyle={{ color: 'var(--primary)' }}
                  />
                  <Area type="monotone" dataKey="searches" stroke="var(--primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorSearches)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-chart-data">No searches performed recently</div>
            )}
          </div>
        </div>

        {/* Platform Share Pie Chart */}
        <div className="chart-wrapper pie-chart-wrap">
          <h4 className="chart-title">Platform Interest Share</h4>
          <div className="chart-container-inner">
            {data.platform_distribution && data.platform_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={data.platform_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {data.platform_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(20, 20, 25, 0.95)',
                      border: '1px solid var(--glass-border)',
                      borderRadius: '12px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '11px', color: 'var(--text-dim)' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-chart-data">No platform usage registered</div>
            )}
          </div>
        </div>

        {/* Category Interest Bar Chart */}
        <div className="chart-wrapper bar-chart-wrap">
          <h4 className="chart-title">Top Category Interests</h4>
          <div className="chart-container-inner">
            {data.category_distribution && data.category_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.category_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(20, 20, 25, 0.95)',
                      border: '1px solid var(--glass-border)',
                      borderRadius: '12px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                    cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                  />
                  <Bar dataKey="value" fill="#14b8a6" radius={[4, 4, 0, 0]}>
                    {data.category_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-chart-data">No category views recorded yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity Timeline Section */}
      <div className="timeline-section-card">
        <h4 className="timeline-sec-title">Recent Activity Timeline</h4>
        <div className="timeline-flow">
          {data.timeline && data.timeline.length > 0 ? (
            data.timeline.map((event, index) => (
              <div key={index} className="timeline-node">
                <div className="timeline-icon-badge">
                  {getTimelineIcon(event.type)}
                </div>
                <div className="timeline-content">
                  <div className="timeline-body-row">
                    <span className="timeline-desc-text">{event.description}</span>
                    {event.platform && (
                      <span className={`timeline-plat-tag platform-${event.platform.toLowerCase()}`}>
                        {event.platform}
                      </span>
                    )}
                  </div>
                  <span className="timeline-timestamp">{formatActivityTime(event.timestamp)}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="timeline-empty">
              <span>No recent activities recorded. Start searching and exploring deals!</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActivityAnalytics;
