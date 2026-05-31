import axios from 'axios';

export function getApiBaseUrl() {
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  let apiUrl;
  if (isLocalhost) {
    apiUrl = process.env.REACT_APP_LOCAL_API_URL?.trim();
    if (apiUrl?.startsWith("REACT_APP_LOCAL_API_URL=")) {
      apiUrl = apiUrl.replace("REACT_APP_LOCAL_API_URL=", "");
    }
    if (!apiUrl) {
      apiUrl = 'http://localhost:5001/api';
    }
  } else {
    apiUrl = process.env.REACT_APP_API_URL?.trim();
    if (apiUrl?.startsWith("REACT_APP_API_URL=")) {
      apiUrl = apiUrl.replace("REACT_APP_API_URL=", "");
    }
  }

  // Development fallback
  if (!apiUrl) {
    apiUrl = "https://buysmart-ai8b.onrender.com/api";
  }

  // Ensure /api suffix exists
  if (!apiUrl.endsWith("/api")) {
    apiUrl += "/api";
  }

  return apiUrl;
}

export const getBaseUrl = () => {
  return getApiBaseUrl().replace('/api', '');
};

const API_BASE_URL = getApiBaseUrl();

console.log("================================");
console.log("Environment:", process.env.NODE_ENV);
console.log("Hostname:", window.location.hostname);
console.log("Active API URL:", API_BASE_URL);
console.log("================================");

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('buysmart_token');
  if (token) {
    if (!config.headers) config.headers = {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor: auto-refresh access token on 401 & global error toasts
let isRefreshing = false;
let failedQueue = [];
let sessionExpiredCallback = null;

export const setSessionExpiredCallback = (callback) => {
  sessionExpiredCallback = callback;
};

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    const originalRequest = error.config;

    // Only attempt refresh on 401, and not for auth endpoints themselves
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/register')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('buysmart_refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
            headers: { Authorization: `Bearer ${refreshToken}` }
          });
          const newAccessToken = data.data.access_token;
          localStorage.setItem('buysmart_token', newAccessToken);
          originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
          processQueue(null, newAccessToken);
          return api(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          localStorage.removeItem('buysmart_token');
          localStorage.removeItem('buysmart_refresh_token');
          if (sessionExpiredCallback) {
            sessionExpiredCallback();
          }
          window.showToast?.('Session expired. Please log in again.', 'warning');
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        isRefreshing = false;
        localStorage.removeItem('buysmart_token');
        if (sessionExpiredCallback) {
          sessionExpiredCallback();
        }
        window.showToast?.('Session expired. Please log in again.', 'warning');
      }
    }

    // Global Error Reporting via Toast
    let errMsg = 'Something went wrong. Please try again.';
    if (error.code === 'ECONNABORTED') {
      errMsg = 'Request timeout. The server took too long to respond.';
    } else if (!error.response) {
      errMsg = 'Network error. Please check your internet connection or server status.';
    } else if (error.response.status === 500) {
      errMsg = 'Internal server error. Our team has been notified.';
    } else if (error.response.data?.message) {
      errMsg = error.response.data.message;
    } else if (error.response.data?.error) {
      errMsg = error.response.data.error;
    }

    // Show toast for non-401 errors
    if (error.response?.status !== 401) {
      window.showToast?.(errMsg, 'error');
    }

    return Promise.reject(error);
  }
);

let searchAbortController = null;

export const searchProducts = async (query, filters = {}, searchId = null) => {
  if (searchAbortController) {
    searchAbortController.abort();
  }
  searchAbortController = new AbortController();

  console.log("Searching:", query);
  console.log("Request URL:", `${API_BASE_URL}/search?query=${query}`);

  try {
    const response = await api.post('/search', { query, filters, search_id: searchId }, {
      signal: searchAbortController.signal,
      timeout: 90000
    });
    console.log("Search API Response:", response.data);
    return response.data;
  } catch (error) {
    if (axios.isCancel(error)) {
      throw new Error('Cancelled');
    }
    throw error;
  }
};

export const getSearchStatus = async (searchId) => {
  const response = await api.get('/search/status', {
    params: { search_id: searchId }
  });
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getProducts = async (params = {}) => {
  const response = await api.get('/products', { params });
  return response.data;
};

export const getProduct = async (productId) => {
  const response = await api.get(`/products/${productId}`);
  return response.data;
};

export const getProductPriceHistory = async (productId) => {
  const response = await api.get(`/products/${productId}/price-history`);
  return response.data;
};

export const getStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

export const triggerScraping = async (data = {}) => {
  const response = await api.post('/scrape', data);
  return response.data;
};

export const getScrapingLogs = async (params = {}) => {
  const response = await api.get('/scraping-logs', { params });
  return response.data;
};

// Auth
export const registerUser = async ({ name, email, phone_number, password }) => {
  const response = await api.post('/auth/register', { name, email, phone_number, password });
  return response.data;
};

export const loginUser = async ({ identifier, password }) => {
  const response = await api.post('/auth/login', { identifier, password });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const logoutUser = async () => {
  const refreshToken = localStorage.getItem('buysmart_refresh_token');
  const response = await api.post('/auth/logout', { refresh_token: refreshToken });
  return response.data;
};

export const updateProfile = async (data) => {
  if (data && (data.current_password || data.new_password)) {
    const response = await api.put('/profile', data);
    return response.data;
  }
  const response = await api.put('/auth/profile', data);
  return response.data;
};

export const changePassword = async ({ current_password, new_password }) => {
  const response = await api.post('/auth/change-password', { current_password, new_password });
  return response.data;
};

// Trending + redirect + wishlist + purchases
export const getTrendingProducts = async (params = {}) => {
  const response = await api.get('/trending/products', { params });
  return response.data;
};

export const createRedirect = async ({ product_id, source, search_query, product_data }) => {
  const response = await api.post('/redirect/create', { product_id, source, search_query, product_data });
  return response.data;
};

export const getWishlist = async () => {
  const response = await api.get('/wishlist');
  return response.data;
};

export const addToWishlist = async (product_id, options = {}) => {
  const response = await api.post('/wishlist', { product_id, ...options });
  return response.data;
};

export const removeFromWishlist = async (product_id) => {
  const response = await api.delete(`/wishlist/${product_id}`);
  return response.data;
};

export const getPurchases = async () => {
  const response = await api.get('/purchases');
  return response.data;
};

export const confirmPurchase = async ({ product_id, platform, status, product_data }) => {
  const response = await api.post('/purchases/confirm', { product_id, platform, status, product_data });
  return response.data;
};

export const getSearchHistory = async (params = {}) => {
  const response = await api.get('/history/search', { params });
  return response.data;
};

export const clearSearchHistory = async () => {
  const response = await api.delete('/history/search');
  return response.data;
};

// Analytics
export const getAnalyticsOverview = async (days = 30) => {
  const response = await api.get('/analytics/overview', { params: { days } });
  return response.data;
};

// Feedback
export const getFeedback = async (params = {}) => {
  const response = await api.get('/feedback', { params });
  return response.data;
};

export const submitFeedback = async (data) => {
  const response = await api.post('/feedback', data);
  return response.data;
};

export const getRecommendations = async (params = {}) => {
  const response = await api.get('/recommendations', { params });
  return response.data;
};

// Admin Endpoints
export const getAdminUsers = async () => {
  const response = await api.get('/admin/users');
  return response.data;
};

export const toggleUserStatus = async (userId, isActive) => {
  const response = await api.post(`/admin/users/${userId}/status`, { is_active: isActive });
  return response.data;
};

export const changeUserRole = async (userId, role) => {
  const response = await api.post(`/admin/users/${userId}/role`, { role });
  return response.data;
};

export const getAdminDashboardStats = async () => {
  const response = await api.get('/admin/stats');
  return response.data;
};

// User Profile & Activity Dashboard Endpoints
export const getProfile = async () => {
  const response = await api.get('/profile');
  return response.data;
};



export const getDashboardOverview = async () => {
  const response = await api.get('/dashboard/overview');
  return response.data;
};

export const getDashboardSearchHistory = async (params = {}) => {
  const response = await api.get('/dashboard/search-history', { params });
  return response.data;
};

export const deleteSearchHistoryEntry = async (eventId) => {
  const response = await api.delete(`/dashboard/search-history/${eventId}`);
  return response.data;
};

export const getDashboardRecentlyViewed = async () => {
  const response = await api.get('/dashboard/recently-viewed');
  return response.data;
};

export const getDashboardWishlist = async (sortBy = 'date_added') => {
  const response = await api.get('/dashboard/wishlist', { params: { sort_by: sortBy } });
  return response.data;
};

export const getDashboardPriceAlerts = async () => {
  const response = await api.get('/dashboard/price-alerts');
  return response.data;
};

export const updatePriceAlert = async (alertId, targetPrice) => {
  const response = await api.put(`/dashboard/price-alerts/${alertId}`, { target_price: targetPrice });
  return response.data;
};

export const deletePriceAlert = async (alertId) => {
  const response = await api.delete(`/dashboard/price-alerts/${alertId}`);
  return response.data;
};

export const getDashboardActivityAnalytics = async () => {
  const response = await api.get('/dashboard/activity-analytics');
  return response.data;
};

export const getDashboardPreferences = async () => {
  const response = await api.get('/dashboard/preferences');
  return response.data;
};

export const getPersonalizedRecommendations = async (params = {}) => {
  const response = await api.get('/recommendations/personalized', { params });
  return response.data;
};

export const submitRecommendationFeedback = async (productId, feedbackType) => {
  const response = await api.post('/recommendations/feedback', { product_id: productId, feedback_type: feedbackType });
  return response.data;
};

// AI Search API endpoints
export const searchProductsAI = async (query) => {
  const response = await api.post('/search/ai', { query });
  return response.data;
};

export const submitAISearchFeedback = async (eventId, feedbackType) => {
  const response = await api.post(`/search/ai/${eventId}/feedback`, { feedback: feedbackType });
  return response.data;
};

export const getDashboardAISearchAnalytics = async () => {
  const response = await api.get('/dashboard/ai-search-analytics');
  return response.data;
};

export default api;



