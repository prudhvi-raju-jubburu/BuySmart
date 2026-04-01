# Buy Smart - Real-Time Product Recommendation and Price Comparison System

A comprehensive e-commerce product comparison and recommendation system that aggregates product data from multiple platforms and provides intelligent recommendations using machine learning and rule-based scoring.

## Project Structure

```
Buy Smart/
├── backend/              # Python Flask backend
│   ├── app.py           # Main Flask application
│   ├── models.py        # Database models
│   ├── scraper.py       # Web scraping module
│   ├── recommender.py   # ML recommendation engine
│   ├── config.py        # Configuration
│   ├── requirements.txt # Python dependencies
│   └── run.py           # Run script
│
├── frontend/            # React frontend
│   ├── src/             # React source code
│   │   ├── components/  # React components
│   │   ├── services/    # API service
│   │   └── App.js       # Main app component
│   ├── public/          # Public assets
│   └── package.json     # Node dependencies
│
└── README.md            # This file
```

## Features

- **Multi-Platform Scraping**: Collects product data from multiple e-commerce platforms (Amazon, Flipkart, etc.)
- **Scheduled Data Updates**: Automatically updates product information at predefined intervals
- **Intelligent Recommendations**: Uses TF-IDF vectorization and cosine similarity for product matching
- **Multi-Criteria Ranking**: Ranks products based on price, rating, platform trust, and review count
- **Real-Time Search**: Fast search and filtering capabilities
- **Modern React Frontend**: Beautiful, responsive user interface built with React

## Technology Stack

### Backend
- Python 3.8+
- Flask (REST API)
- SQLite/PostgreSQL (Database)
- BeautifulSoup4, Selenium (Web Scraping)
- scikit-learn (Machine Learning)

### Frontend
- React 18
- Axios (HTTP Client)
- Modern CSS with responsive design

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js 16+ and npm
- Chrome browser (for Selenium web scraping)

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create a `.env` file (optional)**
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///products.db
   SCRAPING_INTERVAL_HOURS=6
   ```

6. **Initialize the database**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Create `.env` file (optional)**
   ```env
   REACT_APP_API_URL=http://localhost:5000/api
   ```

## Running the Application

### Start Backend

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Run the Flask server**
   ```bash
   python run.py
   ```
   
   Or directly:
   ```bash
   python app.py
   ```

   The backend will run on `http://localhost:5000`

### Start Frontend

1. **Navigate to frontend directory** (in a new terminal)
   ```bash
   cd frontend
   ```

2. **Start the React development server**
   ```bash
   npm start
   ```

   The frontend will run on `http://localhost:3000` and automatically open in your browser.

## API Endpoints

### Search Products
```http
POST /api/search
Content-Type: application/json

{
  "query": "laptop",
  "filters": {
    "min_price": 500,
    "max_price": 2000,
    "platforms": ["Amazon", "Flipkart"],
    "min_rating": 4.0
  },
  "top_n": 20
}
```

### Get All Products
```http
GET /api/products?page=1&per_page=20&platform=Amazon&sort_by=recommendation_score
```

### Get Product by ID
```http
GET /api/products/1
```

### Trigger Manual Scraping
```http
POST /api/scrape
Content-Type: application/json

{
  "platform": "amazon",
  "query": "smartphone",
  "max_results": 20
}
```

### Get Statistics
```http
GET /api/stats
```

### Get Scraping Logs
```http
GET /api/scraping-logs?page=1&per_page=20
```

## System Architecture

### Components

1. **Scraper Module** (`backend/scraper.py`)
   - Base scraper class with common functionality
   - Platform-specific scrapers (Amazon, Flipkart)
   - Scraper manager for coordinating multiple platforms

2. **Recommendation Engine** (`backend/recommender.py`)
   - TF-IDF vectorization for text similarity
   - Cosine similarity calculation
   - Rule-based scoring mechanism
   - Hybrid ranking system

3. **Database Models** (`backend/models.py`)
   - Product model with all product attributes
   - Scraping log model for tracking operations

4. **Flask Application** (`backend/app.py`)
   - RESTful API endpoints
   - Scheduled scraping background task
   - Request handling and response formatting

5. **React Frontend** (`frontend/src/`)
   - Modern, responsive web interface
   - Real-time search and filtering
   - Product display with scores and ratings

### Data Flow

1. **Scheduled Scraping**: Background scheduler runs at configured intervals
2. **Data Collection**: Scrapers collect product data from e-commerce platforms
3. **Data Storage**: Products are stored/updated in the database
4. **Model Training**: TF-IDF model is trained on product descriptions
5. **User Search**: User submits search query via React frontend
6. **Similarity Matching**: System finds similar products using cosine similarity
7. **Scoring & Ranking**: Products are scored and ranked using multi-criteria evaluation
8. **Results Display**: Ranked products are displayed in React frontend

## Configuration

Key configuration options in `backend/config.py`:

- `SCRAPING_INTERVAL_HOURS`: How often to scrape (default: 6 hours)
- `TFIDF_MAX_FEATURES`: Maximum features for TF-IDF (default: 5000)
- `SIMILARITY_THRESHOLD`: Minimum similarity score (default: 0.1)
- `MAX_RECOMMENDATIONS`: Maximum results to return (default: 50)
- Scoring weights:
  - `PRICE_WEIGHT`: 0.3
  - `RATING_WEIGHT`: 0.3
  - `PLATFORM_TRUST_WEIGHT`: 0.2
  - `REVIEW_COUNT_WEIGHT`: 0.2

## Recommendation Algorithm

The system uses a hybrid approach:

1. **Text Similarity (60% weight)**
   - TF-IDF vectorization of product descriptions
   - Cosine similarity between query and products

2. **Multi-Criteria Scoring (40% weight)**
   - Price score (normalized, lower is better)
   - Rating score (normalized to 0-1)
   - Platform trust score
   - Review count score (normalized)

Final ranking combines both scores for optimal recommendations.

## Development

### Backend Development
- Backend runs on port 5000
- Enable CORS for React frontend (already configured)
- Database file: `products.db` (SQLite) in backend directory

### Frontend Development
- Frontend runs on port 3000
- Hot reload enabled in development mode
- API calls proxy to backend automatically (configured in package.json)

## Limitations & Considerations

- **Web Scraping**: E-commerce sites may have anti-scraping measures. Consider using official APIs when available.
- **Rate Limiting**: Built-in delays to respect website resources
- **Legal Compliance**: Ensure compliance with websites' Terms of Service
- **Data Accuracy**: Prices and availability may change frequently
- **Scalability**: For production, consider using a more robust database (PostgreSQL) and caching (Redis)

## Future Enhancements

- Add more e-commerce platforms
- Implement user accounts and personalized recommendations
- Add price history tracking
- Implement email alerts for price drops
- Add product comparison feature
- Implement caching for faster responses
- Add API authentication
- Support for multiple languages

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.
"# BuySmart" 
