import React, { useEffect, useState } from 'react';
import { getDashboardAISearchAnalytics } from '../../services/api';
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Legend
} from 'recharts';

const COLORS = ['#10b981', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#14b8a6'];

const AISearchInsights = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardAISearchAnalytics();
      if (res.success) {
        setData(res.data);
      } else {
        setError(res.message || 'Failed to load AI search insights.');
      }
    } catch (err) {
      setError(err?.response?.data?.message || 'Error loading AI search insights.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  if (loading) {
    return (
      <div className="panel-loading" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '3rem' }}>
        <div className="spinner"></div>
        <span style={{ marginTop: '1rem', color: 'rgba(255,255,255,0.7)' }}>Loading AI search metrics...</span>
      </div>
    );
  }

  if (error) {
    return <div className="error-message" style={{ padding: '2rem', textAlign: 'center', color: '#f87171' }}>{error}</div>;
  }

  if (!data) return null;

  const { stats, events, category_distribution } = data;

  // Prepare feedback data for chart
  const feedbackData = [
    { name: 'Helpful', value: stats.helpful_count },
    { name: 'Not Helpful', value: stats.not_helpful_count }
  ].filter(item => item.value > 0);

  const formattedDate = (isoStr) => {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="ai-insights-container animate-fade-in" style={{ padding: '1rem' }}>
      <div className="panel-header" style={{ marginBottom: '2rem' }}>
        <h3 className="card-title" style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#a855f7' }}>Shopping Insights</h3>
        <span className="subtitle-desc" style={{ color: 'rgba(255,255,255,0.6)' }}>Analyze how you search and what you look for</span>
      </div>

      {/* Metrics Summary Row */}
      <div className="analytics-metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="metric-box blue" style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center' }}>
          <span className="metric-val" style={{ display: 'block', fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>{stats.total_searches}</span>
          <span className="metric-lbl" style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Smart Searches</span>
        </div>
        <div className="metric-box green" style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center' }}>
          <span className="metric-val" style={{ display: 'block', fontSize: '2rem', fontWeight: 'bold', color: '#10b981' }}>{stats.helpful_count}</span>
          <span className="metric-lbl" style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Helpful Queries Rated</span>
        </div>
        <div className="metric-box purple" style={{ background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.2)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center' }}>
          <span className="metric-val" style={{ display: 'block', fontSize: '2rem', fontWeight: 'bold', color: '#a855f7' }}>{stats.satisfaction_rate}%</span>
          <span className="metric-lbl" style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Satisfaction Rate</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="insights-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem', marginBottom: '2.5rem' }}>
        {/* Category distribution */}
        <div className="insight-chart-card glass-card" style={{ padding: '1.5rem', borderRadius: '16px' }}>
          <h4 className="chart-title" style={{ margin: '0 0 1rem 0', color: '#fff', fontSize: '1.1rem' }}>Top Searched Categories</h4>
          {category_distribution && category_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={category_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="category" stroke="rgba(255,255,255,0.6)" fontSize={11} tickLine={false} />
                <YAxis stroke="rgba(255,255,255,0.6)" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(20, 20, 25, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    color: 'white',
                    fontSize: '12px'
                  }}
                  cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                />
                <Bar dataKey="count" fill="#818cf8" radius={[4, 4, 0, 0]}>
                  {category_distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', padding: '4rem', color: 'rgba(255,255,255,0.5)' }}>No category data recorded</div>
          )}
        </div>

        {/* Feedback Share */}
        <div className="insight-chart-card glass-card" style={{ padding: '1.5rem', borderRadius: '16px' }}>
          <h4 className="chart-title" style={{ margin: '0 0 1rem 0', color: '#fff', fontSize: '1.1rem' }}>Search Feedback Summary</h4>
          {feedbackData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={feedbackData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {feedbackData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.name === 'Helpful' ? '#10b981' : '#ef4444'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'rgba(20, 20, 25, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    color: 'white',
                    fontSize: '12px'
                  }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px', color: 'white' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', padding: '4rem', color: 'rgba(255,255,255,0.5)' }}>No search feedback submitted yet</div>
          )}
        </div>
      </div>

      {/* History table */}
      <div className="recent-searches-table-card glass-card" style={{ padding: '1.5rem', borderRadius: '16px' }}>
        <h4 className="chart-title" style={{ margin: '0 0 1rem 0', color: '#fff', fontSize: '1.1rem' }}>Recent Searches</h4>
        {events && events.length > 0 ? (
          <table className="recent-searches-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Query</th>
                <th>Refined Query</th>
                <th>Extracted Category</th>
                <th>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id}>
                  <td>{formattedDate(ev.created_at)}</td>
                  <td style={{ fontWeight: '500' }}>{ev.query}</td>
                  <td style={{ fontStyle: 'italic', opacity: 0.8 }}>{ev.rewritten_query || 'N/A'}</td>
                  <td>
                    <span style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      padding: '0.15rem 0.4rem',
                      fontSize: '0.8rem'
                    }}>
                      {ev.extracted_intent?.category || 'General'}
                    </span>
                  </td>
                  <td>
                    {ev.feedback ? (
                      <span className={`platform-tag ${ev.feedback === 'helpful' ? 'amazon' : 'myntra'}`}>
                        {ev.feedback === 'helpful' ? '👍 Helpful' : '👎 Unhelpful'}
                      </span>
                    ) : (
                      <span style={{ opacity: 0.5, fontSize: '0.85rem' }}>None</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'rgba(255,255,255,0.5)' }}>No recent conversational searches found.</div>
        )}
      </div>
    </div>
  );
};

export default AISearchInsights;
