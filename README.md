# 🛒 BuySmart — Smart Product Discovery & Price Comparison Platform

> **A full-stack AI-assisted e-commerce intelligence platform** that aggregates products from Amazon, Flipkart, Myntra, and Meesho, delivers personalized recommendations, and understands natural language shopping queries — all without depending on external AI APIs for core functionality.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Live Features](#-live-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Recommendation Engine](#-recommendation-engine)
- [AI Search Layer](#-ai-search-layer)
- [Admin Dashboard](#-admin-dashboard)
- [Testing](#-testing)
- [Security](#-security)
- [Screenshots](#-screenshots)
- [Roadmap](#-roadmap)
- [Developer](#-developer)
- [License](#-license)

---

## 🌟 Overview

BuySmart is a modern, production-ready platform designed to solve a real-world problem: finding the best deals across multiple Indian e-commerce platforms without visiting each one individually.

It combines **real-time product scraping**, a **hybrid recommendation engine** (TF-IDF + rule-based ranking), and an **intelligent intent parser** to understand budget, category, brand, and purpose from plain English queries.

### Key Design Principles

| Principle | Implementation |
|---|---|
| **AI-Optional** | System never depends on Gemini/OpenAI for core functionality |
| **Quota Resilience** | 15-minute cooldown on API rate-limit failures; fallback parser activates immediately |
| **Strict Category Enforcement** | Category groups are hard constraints — cross-group results are rejected before scoring |
| **User-Centric** | No technical jargon (scores, confidence, similarity %) exposed to users |
| **Full Test Coverage** | 70+ automated tests across all feature areas |

---

## ✨ Live Features

### 🔍 Smart Product Search

Search products using natural language:

```
Laptop under ₹50,000
Samsung phone with good camera
Best running shoes for jogging
Bluetooth headphones under 3000
Gaming laptop under ₹80,000 for coding
```

BuySmart automatically extracts:
- **Product category** — Laptop, Phone, Shoes, Fashion, Audio, Watch...
- **Budget range** — "under 50k", "₹30,000 to ₹60,000", "below 5000"
- **Brand preference** — Apple, Samsung, Nike, Lenovo, Boat...
- **Purpose/use case** — gaming, coding, machine learning, office, student...
- **Key features** — camera, battery, lightweight, bluetooth, running...
- **Platform preference** — Amazon, Flipkart, Myntra, Meesho

### 🤖 Hybrid Recommendation Engine

- TF-IDF vectorization for semantic similarity
- Multi-factor scoring: relevance × quality × user preference × popularity × specs × freshness
- User behavior analysis (searches, clicks, wishlist, purchases)
- Brand and category diversity balancing
- Deduplication of identical products across platforms

### 💰 Multi-Platform Price Comparison

- Real-time product aggregation from Amazon, Flipkart, Myntra, Meesho
- Side-by-side comparison view
- Platform trust scoring for result ranking

### 📊 User Dashboard

- Shopping history and search timeline
- Saved wishlist with price tracking
- Personalized product suggestions
- Shopping insights and category analytics

### 🔐 Secure Authentication

- JWT access + refresh token flow
- BCrypt password hashing
- Role-based access (User / Admin)
- Account activation / deactivation

### 🛡️ Admin Panel

- Full user management with role control
- Live AI provider status monitoring (Gemini / OpenAI / Fallback)
- Platform performance analytics
- Search intelligence dashboard (top queries, failed searches, trends)
- Scraping monitor with status logs
- Feedback center

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│    Search │ Dashboard │ Profile │ Admin │ Wishlist        │
└──────────────────┬───────────────────────────────────────┘
                   │ HTTP / REST API
┌──────────────────▼───────────────────────────────────────┐
│                    Flask Backend                         │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Routes    │  │  Services   │  │     Models      │  │
│  │  /search    │  │ ai_search   │  │  Product        │  │
│  │  /auth      │  │ recommender │  │  User           │  │
│  │  /dashboard │  │ scraper     │  │  SearchEvent    │  │
│  │  /admin     │  │ ai_status   │  │  ClickEvent     │  │
│  │  /health    │  └─────────────┘  │  WishlistItem   │  │
│  └─────────────┘                   │  AISearchCache  │  │
│                                    └─────────────────┘  │
└──────────────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│               Search Intelligence Layer                  │
│                                                          │
│   Query ──► Cache Check (24h) ──► Gemini (optional)     │
│         ──► OpenAI (optional)  ──► Local Fallback Parser  │
│                                                          │
│   Fallback Parser:  Category │ Budget │ Brand │ Purpose  │
│                     Platform │ Rating │ Features         │
└──────────────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│                    PostgreSQL Database                   │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Frontend
| Technology | Purpose |
|---|---|
| React.js 18 | UI framework |
| React Router v6 | Client-side routing |
| Axios | HTTP client |
| Recharts | Analytics charts |
| Vanilla CSS | Custom design system |
| Glassmorphism UI | Visual design language |

### Backend
| Technology | Purpose |
|---|---|
| Python 3.12 | Runtime |
| Flask 3.1 | Web framework |
| Flask-JWT-Extended | JWT authentication |
| Flask-SQLAlchemy | ORM layer |
| APScheduler | Background job scheduler |
| BCrypt | Password hashing |
| Requests | HTTP client for scrapers |
| BeautifulSoup4 | HTML parsing |
| Selenium / Playwright | JavaScript-rendered pages |

### Machine Learning
| Technology | Purpose |
|---|---|
| Scikit-Learn | TF-IDF vectorization |
| NumPy | Cosine similarity calculations |
| SciPy | Mathematical utilities |
| Pandas | Data manipulation |

### Database
| Technology | Purpose |
|---|---|
| PostgreSQL | Primary database |
| SQLAlchemy ORM | Database abstraction |
| `psycopg2-binary` | PostgreSQL adapter |

### Optional AI Layer
| Technology | Purpose |
|---|---|
| Google Gemini API | Enhanced intent extraction |
| OpenAI GPT-4o-mini | Fallback LLM |
| Local Regex Parser | Always-on fallback (no API needed) |

---

## 📁 Project Structure

```
BuySmart/
│
├── backend/
│   ├── routes/
│   │   ├── search.py          # Search + AI pipeline + rate limiting
│   │   ├── auth.py            # Registration, login, JWT, logout
│   │   ├── dashboard.py       # User analytics, wishlist, history
│   │   ├── admin.py           # Admin endpoints + AI status
│   │   ├── recommendations.py # Personalized recommendations
│   │   └── health.py          # System + DB + AI health check
│   │
│   ├── services/
│   │   ├── recommender.py     # Hybrid recommendation engine
│   │   ├── ai_search.py       # Intent extraction + cache + fallback
│   │   ├── ai_status.py       # Provider cooldown + status monitor
│   │   └── scraper.py         # Multi-platform product scraper
│   │
│   ├── models.py              # All SQLAlchemy models
│   ├── config.py              # Environment configuration
│   ├── app.py                 # Flask app factory + blueprint registration
│   ├── run.py                 # Server entry point
│   ├── requirements.txt       # Python dependencies
│   └── tests/                 # 70+ automated tests
│       ├── conftest.py
│       ├── test_admin.py
│       ├── test_auth.py
│       ├── test_search.py
│       ├── test_search_quality.py
│       ├── test_recommendations.py
│       ├── test_sprint_e.py   # AI resilience + category isolation tests
│       └── ...
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.jsx
│   │   │   ├── SearchPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── ProfilePage.jsx
│   │   │   └── AdminPage.jsx
│   │   │
│   │   ├── components/
│   │   │   ├── Navbar.js
│   │   │   ├── ProductCard.js
│   │   │   ├── SearchSection.js
│   │   │   ├── ai-search/
│   │   │   │   ├── AISearchBar.jsx
│   │   │   │   ├── AISearchPanel.jsx
│   │   │   │   ├── IntentSummary.jsx
│   │   │   │   ├── SearchExplanation.jsx
│   │   │   │   └── SuggestedQueries.jsx
│   │   │   └── dashboard/
│   │   │       ├── PersonalizedRecommendations.jsx
│   │   │       ├── AISearchInsights.jsx
│   │   │       ├── WishlistPanel.js
│   │   │       └── ...
│   │   │
│   │   ├── services/
│   │   │   └── api.js         # Centralized API client
│   │   └── styles/
│   │       └── index.css      # Global design tokens
│   │
│   ├── public/
│   └── package.json
│
├── images/                    # Project screenshots
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **PostgreSQL** 14+ (local or cloud — Neon, Supabase, Railway)

### 1. Clone the Repository

```bash
git clone https://github.com/prudhvi-raju-jubburu/BuySmart.git
cd BuySmart
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the `backend/` directory:

```env
# Required
DATABASE_URL=postgresql://user:password@host:5432/buysmart
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Optional AI enhancement (system works fully without these)
GEMINI_API_KEY=
OPENAI_API_KEY=

# Optional settings
FLASK_ENV=development
SCRAPING_INTERVAL_HOURS=6
```

### 4. Start the Backend

```bash
python run.py
```

Backend available at: `http://localhost:5001/api`

### 5. Frontend Setup

```bash
cd frontend
npm install
```

Create a `.env` file in `frontend/`:

```env
REACT_APP_API_URL=http://localhost:5001/api
```

```bash
npm start
```

Frontend available at: `http://localhost:3000`

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | Flask session secret |
| `JWT_SECRET_KEY` | ✅ | JWT signing secret |
| `GEMINI_API_KEY` | ⬜ | Google Gemini API key (optional) |
| `OPENAI_API_KEY` | ⬜ | OpenAI API key (optional) |
| `FLASK_ENV` | ⬜ | `development` or `production` |
| `SCRAPING_INTERVAL_HOURS` | ⬜ | Background scrape frequency (default: 6) |
| `SIMILARITY_THRESHOLD` | ⬜ | TF-IDF similarity cutoff (default: 0.1) |
| `MAX_RECOMMENDATIONS` | ⬜ | Max products returned (default: 50) |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `REACT_APP_API_URL` | ✅ | Backend API base URL |

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register with email or phone |
| `POST` | `/api/auth/login` | Login with email/phone + password |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/auth/me` | Get current user profile |
| `POST` | `/api/auth/logout` | Invalidate tokens |

### Search

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/search` | Unified natural language search |
| `POST` | `/api/search/feedback` | Submit search result feedback |

**Example Request:**
```json
POST /api/search
{
  "query": "gaming laptop under 80000",
  "filters": {}
}
```

**Example Response:**
```json
{
  "success": true,
  "products": [...],
  "intent": {
    "category": "Laptop",
    "budget_max": 80000,
    "purpose": "gaming",
    "search_explanation_bullets": [
      "✓ Looking for: Laptop",
      "✓ Budget: Under ₹80,000",
      "✓ Purpose: Gaming"
    ],
    "refinements": ["Best gaming laptop reviews", "Affordable gaming laptops", "Branded gaming laptops"]
  }
}
```

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | User activity summary |
| `GET` | `/api/history/search` | Search history |
| `GET` | `/api/recommendations` | Personalized product recommendations |
| `GET` | `/api/wishlist` | Saved wishlist items |
| `POST` | `/api/wishlist` | Add product to wishlist |
| `DELETE` | `/api/wishlist/:id` | Remove from wishlist |

### Admin (Admin JWT required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/users` | List all users with activity stats |
| `POST` | `/api/admin/users/:id/status` | Enable / disable user account |
| `POST` | `/api/admin/users/:id/role` | Promote / demote user role |
| `GET` | `/api/admin/stats` | Full system + AI + platform statistics |
| `GET` | `/api/admin/ai-status` | Live AI provider availability |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Database + AI status check |

**Example Health Response:**
```json
{
  "status": "healthy",
  "database": true,
  "gemini": false,
  "openai": false,
  "fallback_parser": true
}
```

---

## 🧠 Recommendation Engine

The recommendation engine uses a **6-factor weighted scoring model**:

```
Final Score = (0.40 × Relevance)
            + (0.20 × Quality)
            + (0.15 × User Preference)
            + (0.10 × Popularity)
            + (0.10 × Spec Match)
            + (0.05 × Freshness)
```

| Factor | Calculation |
|---|---|
| **Relevance** | TF-IDF cosine similarity between query and product text |
| **Quality** | Rating (35%) + review count (20%) + platform trust (20%) + brand (15%) + completeness (10%) |
| **User Preference** | Category affinity + brand affinity + price range + platform preference (from history) |
| **Popularity** | Normalized review count across the result set |
| **Spec Match** | Hardware spec detection for purpose-specific queries (gaming: GPU, coding: RAM+SSD...) |
| **Freshness** | Recency of product data (full score if < 30 days old) |

### Category Enforcement

Category groups are **hard constraints** — no cross-group results can leak through:

| Group | Includes |
|---|---|
| `fashion` | Fashion, Clothing, Shirt, Jeans, Dress |
| `electronics` | Audio, Earbuds, Headphones, Watch, Smartwatch |
| `laptop` | Laptop, Notebook, Computer |
| `phone` | Phone, Mobile, Smartphone |
| `shoes` | Shoes, Footwear, Sneakers |

---

## 🤖 AI Search Layer

BuySmart uses a **3-tier intent extraction pipeline**:

```
Search Query
     │
     ▼
[1] Cache Check (24-hour TTL)
     │ miss
     ▼
[2] Gemini API (if key set + not on cooldown)
     │ 429 / quota → mark cooldown 15 min
     ▼
[3] OpenAI API (if key set + not on cooldown)
     │ 429 / quota → mark cooldown 15 min
     ▼
[4] Local Fallback Parser (always available)
     │
     ▼
Structured Intent JSON → Ranking Engine
```

The **Local Fallback Parser** extracts:
- Category via keyword matching (12 categories, 100+ keywords)
- Brands (Apple, Samsung, Lenovo, Nike, Adidas, Boat, JBL, and more)
- Budget via regex (supports `₹50,000`, `50k`, `fifty thousand`, range detection)
- Purpose (gaming, coding, machine learning, student, office, video editing...)
- Features (camera, battery, lightweight, bluetooth, running...)
- Platform (Amazon, Flipkart, Myntra, Meesho)

> 📌 **The system operates identically whether or not API keys are configured.**

---

## 🔧 Admin Dashboard

The admin panel provides full operational visibility:

- **User Management** — View all users, toggle active status, promote to admin
- **System Stats** — Total users, searches, clicks, wishlist items, recommendations served
- **AI Status Monitor** — Live Gemini / OpenAI availability, cooldown status, fallback mode
- **Search Intelligence** — Top queries, failed searches, search trends (7-day chart)
- **Platform Analytics** — Product count, average rating, average price per platform
- **Category Popularity** — Most searched categories
- **Scraping Monitor** — Last 10 scraping job statuses and timestamps
- **Feedback Center** — User-submitted search feedback (helpful / not helpful)

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

### Test Coverage

| Test Module | Coverage |
|---|---|
| `test_admin.py` | Admin RBAC, user management, stats endpoint |
| `test_auth.py` | Registration, login, logout, token refresh |
| `test_search.py` | Search pipeline, rate limiting, pagination |
| `test_search_quality.py` | Category filtering, budget enforcement, deduplication |
| `test_recommendations.py` | Personalized ranking, spec boosting |
| `test_sprint_e.py` | AI resilience, cooldown, category isolation, health endpoint |
| `test_dashboard.py` | Wishlist, history, profile operations |
| `test_database.py` | Model integrity, relationships |
| `test_security.py` | SQL injection, XSS, JWT validation |
| `test_performance.py` | Response time benchmarks |
| `test_persistence.py` | Data durability and session handling |
| `test_profile.py` | Profile update, preferences |

**Status: 70+ tests — all passing**

---

## 🔒 Security

| Feature | Implementation |
|---|---|
| Password hashing | BCrypt with per-user salt |
| Authentication | JWT (access + refresh token pattern) |
| Token blacklisting | Logout invalidates refresh tokens |
| Input sanitization | Control character stripping, query length cap |
| SQL injection protection | SQLAlchemy ORM parameterized queries |
| Role-based access control | User / Admin roles, `admin_required` decorator |
| Self-protection | Admins cannot disable or demote their own account |
| Rate limiting | 15 req/min on AI search endpoints (in-memory) |
| CORS configuration | Controlled via Flask-CORS |

---

## 📸 Screenshots

### Homepage
![Homepage](images/homepage.png)

### Login Page
![Login](images/login.png)

### Search Experience
![Search](images/search.png)

---

## 🗺️ Roadmap

- [ ] Real-time price drop notifications (email + in-app)
- [ ] Price history chart per product
- [ ] Browser extension for instant BuySmart comparison
- [ ] Voice-based product search
- [ ] Mobile application (React Native)
- [ ] More platform integrations (Snapdeal, Ajio, Nykaa)
- [ ] Social wishlist sharing
- [ ] Product review sentiment analysis

---

## 👨‍💻 Developer

**Jubburu Prudhvi Raju**

B.Tech — Computer Science & Engineering  
Full Stack Developer (React · Python · Flask · PostgreSQL)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/jubburu-prudhvi-raju)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?logo=github)](https://github.com/prudhvi-raju-jubburu)

---

## 📄 License

This project is developed for **educational, research, and portfolio purposes**.

```
© 2024–2026 Jubburu Prudhvi Raju. All rights reserved.
```