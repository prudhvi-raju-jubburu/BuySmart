import React, { useState, useEffect, useCallback } from 'react';
import './styles/App.css';
import Header from './components/Header';
import TrendingSection from './components/TrendingSection';
import Navbar from './components/Navbar';
import UserPanel from './components/UserPanel';
import Modal from './components/Modal';
import ComparisonChart from './components/ComparisonChart';
import NotificationTicker from './components/NotificationTicker';
import ErrorBoundary from './components/ErrorBoundary';
import { searchProducts, getStats, getMe, getSearchHistory, clearSearchHistory, submitAISearchFeedback, setSessionExpiredCallback } from './services/api';
import { ToastContainer } from './components/Toast';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';

import Footer from './components/Footer';
import FloatingFeedback from './components/FloatingFeedback';

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [userPanelOpen, setUserPanelOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('search');
  const [theme, setTheme] = useState(localStorage.getItem('buysmart_theme') || 'dark');
  const [filters, setFilters] = useState({
    minPrice: '',
    maxPrice: '',
    platforms: ['Amazon', 'Flipkart', 'Meesho', 'Myntra'],
    minRating: '',
    fastMode: true,
    includeLiveScraping: true
  });
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [showComparison, setShowComparison] = useState(false);
  const [history, setHistory] = useState([]);

  // Toast system
  const [toasts, setToasts] = useState([]);
  const showToast = useCallback((message, type = 'success', duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type, duration }]);
  }, []);
  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-theme' : '';
    localStorage.setItem('buysmart_theme', theme);
  }, [theme]);

  // Guard: redirect to login if accessing protected tabs without auth
  useEffect(() => {
    if (activeTab === 'profile' && !user) setActiveTab('login');
    if (activeTab === 'dashboard' && !user) setActiveTab('login');
    if (activeTab === 'admin-dashboard' && (!user || (user.role !== 'admin' && !user.is_admin))) {
      setActiveTab('home');
    }
    // Redirect away from login/register if already logged in
    if ((activeTab === 'login' || activeTab === 'register') && user) setActiveTab('search');
  }, [user, activeTab]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const toggleProductSelection = (product) => {
    setSelectedProducts(prev => {
      if (prev.find(p => p.id === product.id)) {
        return prev.filter(p => p.id !== product.id);
      } else {
        if (prev.length >= 3) {
          alert('You can compare up to 3 products');
          return prev;
        }
        return [...prev, product];
      }
    });
  };

  useEffect(() => {
    setSessionExpiredCallback(() => {
      setUser(null);
      setActiveTab('login');
      showToast('⚠️ Session expired. Please log in again.', 'warning');
    });
    loadStats();
    bootstrapAuth();
  }, [showToast]);

  const bootstrapAuth = async () => {
    const token = localStorage.getItem('buysmart_token');
    if (!token) {
      await refreshUserData();
      return;
    }
    try {
      const data = await getMe();
      setUser(data.data?.user || data.user);
      await refreshUserData();
    } catch (_e) {
      localStorage.removeItem('buysmart_token');
      localStorage.removeItem('buysmart_refresh_token');
      setUser(null);
      await refreshUserData();
    }
  };

  const refreshUserData = async () => {
    try {
      if (user) {
        const h = await getSearchHistory({ limit: 10 });
        setHistory(h.items || []);
      } else {
        const guestHistory = JSON.parse(localStorage.getItem('buysmart_guest_history') || '[]');
        setHistory(guestHistory);
      }
    } catch (_e) {
      // Fallback to local on error
      const guestHistory = JSON.parse(localStorage.getItem('buysmart_guest_history') || '[]');
      setHistory(guestHistory);
    }
  };

  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleFooterNavigate = (tab, searchQuery = '') => {
    setActiveTab(tab);
    if (searchQuery) {
      handleSearch(searchQuery, {
        minPrice: '',
        maxPrice: '',
        platforms: [],
        minRating: ''
      });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearch = async (query, searchFilters) => {
    if (!query.trim()) {
      alert('Please enter a search query');
      return;
    }

    setActiveTab('search');
    setLoading(true);
    setSearchQuery(query);
    setFilters(searchFilters);

    try {
      const results = await searchProducts(query, searchFilters);
      setProducts(results.products || results.results || []);
      setSearchResult(results);

      if (results.message) {
        console.info(results.message);
      }

      // Handle Guest History (if not logged in)
      if (!user) {
        const guestHistory = JSON.parse(localStorage.getItem('buysmart_guest_history') || '[]');
        const newEntry = {
          id: Date.now(),
          query: query,
          filters_json: JSON.stringify(searchFilters),
          created_at: new Date().toISOString()
        };
        // Avoid duplicate consecutive searches
        if (guestHistory[0]?.query !== query) {
          const updatedHistory = [newEntry, ...guestHistory].slice(0, 10);
          localStorage.setItem('buysmart_guest_history', JSON.stringify(updatedHistory));
          setHistory(updatedHistory);
        }
      }

      // Reload server-side content if logged in
      if (user) {
        await Promise.all([loadStats(), refreshUserData()]);
      }
    } catch (error) {
      console.error('Error searching products:', error);
      alert('Error searching for products. Please try again.');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearFilters = () => {
    setFilters({
      minPrice: '',
      maxPrice: '',
      platforms: ['Amazon', 'Flipkart', 'Meesho', 'Myntra'],
      minRating: '',
      fastMode: true,
      includeLiveScraping: true
    });
  };

  const handleClearHistory = async () => {
    try {
      if (user) {
        await clearSearchHistory();
      }
      localStorage.removeItem('buysmart_guest_history');
      setHistory([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };

  return (
    <div className="App">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <Navbar
        user={user}
        onAuthChange={async (u) => {
          setUser(u);
          if (u) await refreshUserData();
        }}
        onOpenSection={(id) => setActiveTab(id)}
        onOpenProfile={() => setActiveTab('profile')}
        theme={theme}
        onToggleTheme={toggleTheme}
        activeTab={activeTab}
      />

      {/* Full-screen auth pages (outside scroll area) */}
      {activeTab === 'login' && (
        <LoginPage
          onAuthChange={async (u) => { setUser(u); if (u) await refreshUserData(); }}
          onNavigate={setActiveTab}
          onShowToast={showToast}
        />
      )}
      {activeTab === 'register' && (
        <RegisterPage
          onAuthChange={async (u) => { setUser(u); if (u) await refreshUserData(); }}
          onNavigate={setActiveTab}
          onShowToast={showToast}
        />
      )}
      {activeTab === 'profile' && user && (
        <div className="main-scroll-area">
          <ErrorBoundary>
            <ProfilePage
              user={user}
              onProfileUpdate={(u) => setUser(u)}
              onNavigate={setActiveTab}
              onShowToast={showToast}
            />
          </ErrorBoundary>
        </div>
      )}

      {/* Main app (only shown when not on auth/profile pages) */}
      {!['login', 'register', 'profile', 'dashboard'].includes(activeTab) && (
        <div className="main-scroll-area">
          <NotificationTicker />
          {activeTab !== 'home' && <Header />}
          <UserPanel
            open={userPanelOpen}
            user={user}
            onClose={() => setUserPanelOpen(false)}
            onLogout={() => setUser(null)}
          />
          {activeTab === 'search' && (
            <SearchPage
              user={user}
              loading={loading}
              products={products}
              searchQuery={searchQuery}
              searchResult={searchResult}
              filters={filters}
              selectedProducts={selectedProducts}
              onSearch={handleSearch}
              onClearFilters={handleClearFilters}
              onToggleSelect={toggleProductSelection}
              onSubmitAISearchFeedback={submitAISearchFeedback}
            />
          )}

          {selectedProducts.length > 0 && (
            <div className="comparison-bar">
              <div>
                <strong>{selectedProducts.length}</strong> products selected
              </div>
              <button className="compare-btn" onClick={() => setShowComparison(true)}>Compare Now</button>
              <button className="clear-btn" onClick={() => setSelectedProducts([])}>Clear Selected</button>
            </div>
          )}

          <Modal isOpen={showComparison} onClose={() => setShowComparison(false)} title="Product Comparison">
            <ComparisonChart products={selectedProducts} />
          </Modal>

          {activeTab === 'home' && (
            <HomePage user={user} onSearch={handleSearch} filters={filters} />
          )}

          {activeTab === 'trending' && (
            <div className="container tab-content">
              <TrendingSection user={user} />
            </div>
          )}

          {activeTab === 'admin-dashboard' && user && (user.role === 'admin' || user.is_admin) && (
            <div className="tab-content" style={{ width: '100%' }}>
              <ErrorBoundary>
                <AdminPage user={user} />
              </ErrorBoundary>
            </div>
          )}

          <Footer
            onOpenFeedback={() => setFeedbackOpen(true)}
            onNavigate={handleFooterNavigate}
          />
          <FloatingFeedback
            isOpen={feedbackOpen}
            onToggle={setFeedbackOpen}
            user={user}
          />
        </div>
      )}

      {activeTab === 'dashboard' && user && (
        <div className="main-scroll-area">
          <ErrorBoundary>
            <DashboardPage user={user} onNavigate={setActiveTab} />
          </ErrorBoundary>
        </div>
      )}
    </div>
  );
}

export default App;


