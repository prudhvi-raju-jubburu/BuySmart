import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import SearchSection from './components/SearchSection';
import ProductGrid from './components/ProductGrid';
import LoadingSpinner from './components/LoadingSpinner';
import TrendingSection from './components/TrendingSection';
import Navbar from './components/Navbar';
import HomePlatforms from './components/HomePlatforms';
import Recommendations from './components/Recommendations';
import UserPanel from './components/UserPanel';
import Modal from './components/Modal';
import ComparisonChart from './components/ComparisonChart';
import SearchAnalytics from './components/SearchAnalytics';
import NotificationTicker from './components/NotificationTicker';
import { searchProducts, getStats, getMe, getWishlist, getPurchases, getSearchHistory, clearSearchHistory } from './services/api';

import Footer from './components/Footer';
import FloatingFeedback from './components/FloatingFeedback';

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState(null);
  const [userPanelOpen, setUserPanelOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('search'); // home | search | trending | analytics
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

  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-theme' : '';
    localStorage.setItem('buysmart_theme', theme);
  }, [theme]);

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
    loadStats();
    bootstrapAuth();
  }, []);

  const bootstrapAuth = async () => {
    const token = localStorage.getItem('buysmart_token');
    if (!token) {
      await refreshUserData();
      return;
    }
    try {
      const data = await getMe();
      setUser(data.user);
      await refreshUserData();
    } catch (_e) {
      localStorage.removeItem('buysmart_token');
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

    setLoading(true);
    setSearchQuery(query);
    setFilters(searchFilters);

    try {
      const results = await searchProducts(query, searchFilters);
      setProducts(results.results || []);

      if (results.message) {
        console.log(results.message);
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
      <Navbar
        user={user}
        onAuthChange={async (u) => {
          setUser(u);
          if (u) {
            await refreshUserData();
          }
        }}
        onOpenSection={(id) => setActiveTab(id)}
        onOpenProfile={() => setUserPanelOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <div className="main-scroll-area">
        <NotificationTicker />
        <Header />
        <UserPanel
          open={userPanelOpen}
          user={user}
          onClose={() => setUserPanelOpen(false)}
          onLogout={() => setUser(null)}
        />
        {activeTab === 'search' && (
          <main className="container main-content">
            <SearchSection
              onSearch={handleSearch}
              filters={filters}
              onClearFilters={handleClearFilters}
              user={user}
            />
            {loading ? (
              <LoadingSpinner />
            ) : (
              <>
                {products.length > 0 && <SearchAnalytics products={products} />}
                <ProductGrid
                  products={products}
                  searchQuery={searchQuery}
                  user={user}
                  selectedProducts={selectedProducts}
                  onToggleSelect={toggleProductSelection}
                />
              </>
            )}
          </main>
        )}

        {selectedProducts.length > 0 && (
          <div className="comparison-bar">
            <div>
              <strong>{selectedProducts.length}</strong> products selected
            </div>
            <button
              className="compare-btn"
              onClick={() => setShowComparison(true)}
            >
              Compare Now
            </button>
            <button
              className="clear-btn"
              onClick={() => setSelectedProducts([])}
            >
              Clear Selected
            </button>
          </div>
        )}

        <Modal isOpen={showComparison} onClose={() => setShowComparison(false)} title="Product Comparison">
          <ComparisonChart products={selectedProducts} />
        </Modal>

        {activeTab === 'home' && (
          <div className="container tab-content">
            <HomePlatforms />
            <Recommendations user={user} />
          </div>
        )}

        {activeTab === 'trending' && (
          <div className="container tab-content">
            <TrendingSection user={user} />
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
    </div>
  );
}

export default App;


