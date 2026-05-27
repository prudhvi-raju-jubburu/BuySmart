import React, { useState, useEffect } from 'react';
import { 
  getAdminUsers, 
  toggleUserStatus, 
  changeUserRole, 
  getAdminDashboardStats 
} from '../services/api';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  PieChart, 
  Pie, 
  Cell, 
  Legend, 
  BarChart, 
  Bar 
} from 'recharts';
import './AdminPage.css';
import { SkeletonTable } from '../components/SkeletonCard';

const PLATFORM_COLORS = {
  'Amazon': '#FF9900',
  'Flipkart': '#2874F0',
  'Myntra': '#FF3F6C',
  'Meesho': '#F43397'
};

const CATEGORY_COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00C49F', '#FFBB28', '#FF8042', '#0088FE'];

const AdminPage = ({ user: currentUser }) => {
  const [activeSubTab, setActiveSubTab] = useState('overview'); // overview | users | analytics | scraping | feedback
  const [stats, setStats] = useState(null);
  const [usersList, setUsersList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, usersRes] = await Promise.all([
        getAdminDashboardStats(),
        getAdminUsers()
      ]);
      if (statsRes.success) setStats(statsRes.data);
      if (usersRes.success) setUsersList(usersRes.data.users);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      setError(err.response?.data?.message || "Failed to load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);



  const handleToggleStatus = async (user) => {
    if (currentUser && user.id === currentUser.id) {
      alert("You cannot disable your own account.");
      return;
    }
    setActionBusy(true);
    try {
      const res = await toggleUserStatus(user.id, !user.is_active);
      if (res.success) {
        setUsersList(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u));
        fetchDashboardData();
      }
    } catch (err) {
      alert(err.response?.data?.message || "Failed to update user status.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleChangeRole = async (user, newRole) => {
    if (currentUser && user.id === currentUser.id) {
      alert("You cannot modify your own role.");
      return;
    }
    setActionBusy(true);
    try {
      const res = await changeUserRole(user.id, newRole);
      if (res.success) {
        setUsersList(prev => prev.map(u => u.id === user.id ? { ...u, role: newRole, is_admin: newRole === 'admin' } : u));
        fetchDashboardData();
      }
    } catch (err) {
      alert(err.response?.data?.message || "Failed to update user role.");
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard-container">
        <div className="admin-sidebar">
          <div className="admin-sidebar-header">
            <h3>Admin Panel</h3>
            <span>Loading Console...</span>
          </div>
        </div>
        <div className="admin-main-content" style={{ padding: '32px', width: '100%', boxSizing: 'border-box' }}>
          <div className="page-header-card" style={{ marginBottom: '24px' }}>
            <h2 className="page-title">Loading Admin Workspace</h2>
            <p className="page-subtitle">Fetching operational metrics and user accounts...</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <SkeletonTable />
            <SkeletonTable />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-error-container">
        <div className="admin-error-card">
          <h3>Error Loading Dashboard</h3>
          <p>{error}</p>
          <button className="admin-retry-btn" onClick={fetchDashboardData}>Retry</button>
        </div>
      </div>
    );
  }

  const { overview, user_growth, most_active_users, platform_performance, search_intelligence, scraping_monitor, feedback_center } = stats || {};

  // Formats data for Platform Distribution PieChart
  const pieData = (platform_performance || []).map(p => ({
    name: p.platform || 'Unknown',
    value: p.products || 0
  }));

  return (
    <div className="admin-dashboard-container">
      <div className="admin-sidebar">
        <div className="admin-sidebar-header">
          <h3>Admin Panel</h3>
          <span>Workspace Console</span>
        </div>
        <div className="admin-sidebar-menu">
          <button 
            className={`admin-menu-item ${activeSubTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('overview')}
          >
            📊 System Overview
          </button>
          <button 
            className={`admin-menu-item ${activeSubTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('users')}
          >
            👥 User Management
          </button>
          <button 
            className={`admin-menu-item ${activeSubTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('analytics')}
          >
            📈 Search & Platforms
          </button>
          <button 
            className={`admin-menu-item ${activeSubTab === 'scraping' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('scraping')}
          >
            ⚙️ Scraping Monitor
          </button>
          <button 
            className={`admin-menu-item ${activeSubTab === 'feedback' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('feedback')}
          >
            💬 Feedback Center
          </button>
        </div>
        <div className="admin-sidebar-footer">
          <button className="admin-refresh-btn" onClick={fetchDashboardData}>🔄 Refresh Console</button>
        </div>
      </div>

      <div className="admin-main-content">
        {activeSubTab === 'overview' && (
          <div className="admin-view-tab animate-fade-in">
            <h2 className="admin-section-title">Overview Dashboard</h2>
            
            {/* KPI Cards Grid */}
            <div className="admin-kpi-grid">
              <div className="admin-kpi-card purple">
                <div className="admin-kpi-icon">👥</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.total_users || 0}</span>
                  <span className="admin-kpi-label">Total Users</span>
                </div>
              </div>
              <div className="admin-kpi-card blue">
                <div className="admin-kpi-icon">📦</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.total_products || 0}</span>
                  <span className="admin-kpi-label">Total Products</span>
                </div>
              </div>
              <div className="admin-kpi-card green">
                <div className="admin-kpi-icon">🔍</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.total_searches || 0}</span>
                  <span className="admin-kpi-label">Total Searches</span>
                </div>
              </div>
              <div className="admin-kpi-card yellow">
                <div className="admin-kpi-icon">🖱️</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.total_clicks || 0}</span>
                  <span className="admin-kpi-label">Total Clicks</span>
                </div>
              </div>
              <div className="admin-kpi-card orange">
                <div className="admin-kpi-icon">❤️</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.wishlist_count || 0}</span>
                  <span className="admin-kpi-label">Wishlist Items</span>
                </div>
              </div>
              <div className="admin-kpi-card pink">
                <div className="admin-kpi-icon">🛍️</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.purchase_count || 0}</span>
                  <span className="admin-kpi-label">Purchases</span>
                </div>
              </div>
              <div className="admin-kpi-card teal double">
                <div className="admin-kpi-icon">⚡</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.recommendation_ctr || 0}%</span>
                  <span className="admin-kpi-label">People Who Clicked Suggestions (Shown: {overview?.recommendations_served || 0} | Clicked: {overview?.recommendation_clicks || 0})</span>
                </div>
              </div>
              <div className="admin-kpi-card blue">
                <div className="admin-kpi-icon">🤖</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.total_ai_searches || 0}</span>
                  <span className="admin-kpi-label">AI Searches</span>
                </div>
              </div>
              <div className="admin-kpi-card green">
                <div className="admin-kpi-icon">🎯</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.ai_search_success_rate || 0}%</span>
                  <span className="admin-kpi-label">AI Success Rate</span>
                </div>
              </div>
              <div className="admin-kpi-card orange">
                <div className="admin-kpi-icon">👍</div>
                <div className="admin-kpi-info">
                  <span className="admin-kpi-value">{overview?.ai_helpful_count || 0} / {overview?.ai_not_helpful_count || 0}</span>
                  <span className="admin-kpi-label">AI Helpful / Unhelpful</span>
                </div>
              </div>
            </div>

            {/* Growth & Active Users Section */}
            <div className="admin-grid-two-columns">
              <div className="admin-content-card">
                <h3 className="card-title">📈 User Growth Analytics</h3>
                <div className="admin-growth-grid">
                  <div className="growth-subcard">
                    <span className="growth-value">+{user_growth?.today || 0}</span>
                    <span className="growth-label">Registered Today</span>
                  </div>
                  <div className="growth-subcard">
                    <span className="growth-value">+{user_growth?.week || 0}</span>
                    <span className="growth-label">This Week</span>
                  </div>
                  <div className="growth-subcard">
                    <span className="growth-value">+{user_growth?.month || 0}</span>
                    <span className="growth-label">This Month</span>
                  </div>
                </div>
              </div>

              <div className="admin-content-card">
                <h3 className="card-title">🏆 Top Active Users</h3>
                <div className="admin-table-container min">
                  <table className="admin-table min">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Searches</th>
                        <th>Clicks</th>
                        <th>Total Activity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(most_active_users || []).length > 0 ? (
                        (most_active_users || []).map(u => (
                          <tr key={u.id}>
                            <td data-label="User">
                              <div className="active-user-cell">
                                <span className="active-user-name">{u.name}</span>
                                <span className="active-user-email">{u.email}</span>
                              </div>
                            </td>
                            <td data-label="Searches">{u.searches}</td>
                            <td data-label="Clicks">{u.clicks}</td>
                            <td data-label="Total Activity" className="bold">{u.total}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="4" className="empty-cell" data-label="Status">No active users recorded.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'users' && (
          <div className="admin-view-tab animate-fade-in">
            <h2 className="admin-section-title">User Management</h2>
            <div className="admin-content-card">
              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>User Info</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Activity Metrics</th>
                      <th>Account Info</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList && usersList.length > 0 ? (
                      usersList.map(u => {
                        const isSelf = currentUser && u.id === currentUser.id;
                        return (
                          <tr key={u.id} className={isSelf ? 'self-row' : ''}>
                            <td data-label="User Info">
                              <div className="user-info-cell">
                                <div className="user-avatar-small">
                                  {(u.name && u.name[0]) ? u.name[0].toUpperCase() : '?'}
                                </div>
                                <div>
                                  <div className="user-name-bold">{u.name || 'Unknown User'} {isSelf && <span className="self-tag">(You)</span>}</div>
                                  <div className="user-email-sub">{u.email}</div>
                                </div>
                              </div>
                            </td>
                            <td data-label="Role">
                              <select 
                                className="admin-select"
                                value={u.role}
                                onChange={(e) => handleChangeRole(u, e.target.value)}
                                disabled={isSelf || actionBusy}
                              >
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td data-label="Status">
                              <span className={`status-badge ${u.is_active ? 'active' : 'disabled'}`}>
                                {u.is_active ? 'Active' : 'Disabled'}
                              </span>
                            </td>
                            <td data-label="Activity Metrics">
                              <div className="user-stats-grid">
                                <span>🔍 {u.stats?.searches || 0} searches</span>
                                <span>🖱️ {u.stats?.clicks || 0} clicks</span>
                                <span>❤️ {u.stats?.wishlist || 0} wishlist</span>
                                <span>🛍️ {u.stats?.purchases || 0} purchases</span>
                              </div>
                            </td>
                            <td data-label="Account Info">
                              <div className="user-dates">
                                <div>Joined: {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</div>
                                <div>Login: {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</div>
                              </div>
                            </td>
                            <td data-label="Actions">
                              <button
                                className={`admin-btn-action ${u.is_active ? 'disable' : 'enable'}`}
                                onClick={() => handleToggleStatus(u)}
                                disabled={isSelf || actionBusy}
                              >
                                {u.is_active ? 'Disable' : 'Enable'}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="6" className="empty-cell" data-label="Status">No users registered yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'analytics' && (
          <div className="admin-view-tab animate-fade-in">
            <h2 className="admin-section-title">Metrics & Search Trends</h2>
            
            {/* Recharts Graphs Area */}
            <div className="admin-charts-grid">
              {/* Chart 1: Search Trend */}
              <div className="admin-content-card chart-card">
                <h3 className="card-title">🔍 Search Volume Trend (Last 7 Days)</h3>
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart 
                      data={search_intelligence?.search_trends || []}
                      margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="searchGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#82ca9d" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="day" stroke="#a0a0a0" fontSize={11} />
                      <YAxis stroke="#a0a0a0" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 30, 40, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
                      <Area type="monotone" dataKey="searches" stroke="#82ca9d" fillOpacity={1} fill="url(#searchGrad)" name="Searches" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Platform Distribution */}
              <div className="admin-content-card chart-card">
                <h3 className="card-title">📦 Scraped Products by Platform</h3>
                <div className="chart-wrapper pie-wrapper">
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="45%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PLATFORM_COLORS[entry.name] || '#8884d8'} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 30, 40, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 3: Category Popularity */}
              <div className="admin-content-card chart-card double-width">
                <h3 className="card-title">🏷️ Product Categories Distribution</h3>
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart
                      data={search_intelligence?.category_popularity || []}
                      margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="category" stroke="#a0a0a0" fontSize={11} />
                      <YAxis stroke="#a0a0a0" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 30, 40, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]} name="Products count">
                        {(search_intelligence?.category_popularity || []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Tables for analytics details */}
            <div className="admin-grid-two-columns" style={{ marginTop: '20px' }}>
              {/* Platform Performance Table */}
              <div className="admin-content-card">
                <h3 className="card-title">⚡ Platform Scraper Performance</h3>
                <div className="admin-table-container min">
                  <table className="admin-table min">
                    <thead>
                      <tr>
                        <th>Platform</th>
                        <th>Scraped Products</th>
                        <th>Avg Rating</th>
                        <th>Avg Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(platform_performance || []).map(p => (
                        <tr key={p.platform || Math.random()}>
                          <td data-label="Platform" style={{ color: PLATFORM_COLORS[p.platform] || '#fff', fontWeight: 'bold' }}>{p.platform}</td>
                          <td data-label="Scraped Products">{p.products}</td>
                          <td data-label="Avg Rating">⭐ {p.avg_rating} / 5.0</td>
                          <td data-label="Avg Price">₹{p.avg_price.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Search Intelligence Details */}
              <div className="admin-content-card">
                <h3 className="card-title">🔑 Search Terms Activity</h3>
                <div className="search-intel-split">
                  <div className="search-intel-col">
                    <h4>🔥 Top Searches</h4>
                    <ul className="search-intel-list">
                      {search_intelligence?.top_searches && search_intelligence.top_searches.length > 0 ? (
                        search_intelligence.top_searches.slice(0, 5).map((s, idx) => (
                          <li key={idx}>
                            <span className="search-idx">{idx + 1}</span>
                            <span className="search-text">{s.query}</span>
                            <span className="search-count">{s.count} searches</span>
                          </li>
                        ))
                      ) : (
                        <li className="search-empty">No search events.</li>
                      )}
                    </ul>
                  </div>
                  <div className="search-intel-col">
                    <h4>⚠️ Failed Searches</h4>
                    <ul className="search-intel-list failed">
                      {search_intelligence?.failed_searches && search_intelligence.failed_searches.length > 0 ? (
                        search_intelligence.failed_searches.slice(0, 5).map((s, idx) => (
                          <li key={idx}>
                            <span className="search-idx">{idx + 1}</span>
                            <span className="search-text">{s.query}</span>
                            <span className="search-count">{s.count} failed</span>
                          </li>
                        ))
                      ) : (
                        <li className="search-empty">No failed searches.</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Search Intelligence Panel */}
            <div className="admin-grid-two-columns" style={{ marginTop: '20px' }}>
              <div className="admin-content-card">
                <h3 className="card-title">🤖 AI Search Category Popularity</h3>
                <div className="admin-table-container min">
                  <table className="admin-table min">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>AI Queries Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview?.top_ai_categories && overview.top_ai_categories.length > 0 ? (
                        overview.top_ai_categories.map((c, idx) => (
                          <tr key={idx}>
                            <td data-label="Category" className="bold">{c.category}</td>
                            <td data-label="AI Queries Count">{c.count} times</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="2" className="empty-cell" data-label="Status">No AI categories recorded.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="admin-content-card">
                <h3 className="card-title">🏷️ AI Search Brand Popularity</h3>
                <div className="admin-table-container min">
                  <table className="admin-table min">
                    <thead>
                      <tr>
                        <th>Brand</th>
                        <th>AI Queries Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview?.top_ai_brands && overview.top_ai_brands.length > 0 ? (
                        overview.top_ai_brands.map((b, idx) => (
                          <tr key={idx}>
                            <td data-label="Brand" className="bold">{b.brand}</td>
                            <td data-label="AI Queries Count">{b.count} times</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="2" className="empty-cell" data-label="Status">No AI brands recorded.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'scraping' && (
          <div className="admin-view-tab animate-fade-in">
            <h2 className="admin-section-title">Scraping Operations Monitor</h2>
            <div className="admin-content-card">
              <h3 className="card-title">⚙️ Recent Scraping Executions</h3>
              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Platform</th>
                      <th>Status</th>
                      <th>Products Scraped</th>
                      <th>Execution Time</th>
                      <th>Duration</th>
                      <th>Errors</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(scraping_monitor || []).length > 0 ? (
                      (scraping_monitor || []).map(log => (
                        <tr key={log.id}>
                          <td data-label="Platform" style={{ color: PLATFORM_COLORS[log.platform ? log.platform.charAt(0).toUpperCase() + log.platform.slice(1) : ''] || '#fff', fontWeight: 'bold' }}>
                            {log.platform ? log.platform.toUpperCase() : 'UNKNOWN'}
                          </td>
                          <td data-label="Status">
                            <span className={`status-badge scraping-${log.status}`}>
                              {log.status.toUpperCase()}
                            </span>
                          </td>
                          <td data-label="Products Scraped">{log.products_scraped} products</td>
                          <td data-label="Execution Time">{log.started_at ? new Date(log.started_at).toLocaleString() : 'N/A'}</td>
                          <td data-label="Duration">{log.duration_seconds ? `${log.duration_seconds.toFixed(2)}s` : 'N/A'}</td>
                          <td data-label="Errors" className="error-log-cell" title={log.errors || 'None'}>
                            {log.errors ? log.errors.substring(0, 60) + (log.errors.length > 60 ? '...' : '') : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="6" className="empty-cell" data-label="Status">No scraping operations logged.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'feedback' && (
          <div className="admin-view-tab animate-fade-in">
            <h2 className="admin-section-title">Feedback Center</h2>
            <div className="admin-feedback-cards">
              {feedback_center && feedback_center.length > 0 ? (
                feedback_center.map(feedback => (
                  <div key={feedback.id} className="admin-feedback-card">
                    <div className="feedback-card-header">
                      <div className="feedback-user-info">
                        <span className="feedback-username">{feedback.name || 'Anonymous User'}</span>
                        <span className="feedback-date">
                          {feedback.created_at ? new Date(feedback.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                      <div className="feedback-rating">
                        {'★'.repeat(feedback.rating)}{'☆'.repeat(5 - feedback.rating)}
                      </div>
                    </div>
                    <div className="feedback-card-body">
                      <p className="feedback-text">"{feedback.description}"</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="admin-content-card empty-feedback">
                  <p>No feedback submissions found.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;
