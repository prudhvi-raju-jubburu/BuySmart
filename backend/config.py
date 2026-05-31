import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Config:
    """Application Configuration"""

    # =====================================================
    # Security
    # =====================================================
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "change-this-secret-key-in-production"
    )

    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        "change-this-jwt-secret-in-production"
    )

    # =====================================================
    # =====================================================
    # Database (PostgreSQL ONLY)
    # =====================================================
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please configure your PostgreSQL connection in backend/.env."
        )

    # Enforce PostgreSQL connection string format (except during testing)
    is_testing = os.environ.get("TESTING") == "1" or os.environ.get("PYTEST_CURRENT_TEST") is not None
    if not is_testing:
        if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
            raise RuntimeError(
                f"DATABASE_URL must be a PostgreSQL connection string (got '{DATABASE_URL}')."
            )

    # Render compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pool settings (Neon/Postgres resilient)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    @staticmethod
    def validate_environment():
        """Checks critical env variables on startup and fails fast if missing"""
        db_url = Config.DATABASE_URL
        if not db_url:
            raise RuntimeError("DATABASE_URL environment variable is not set.")
        is_testing = os.environ.get("TESTING") == "1" or os.environ.get("PYTEST_CURRENT_TEST") is not None
        if not is_testing:
            if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
                raise RuntimeError("DATABASE_URL must be a PostgreSQL connection string.")

        secret = os.environ.get("SECRET_KEY")
        if not secret or secret == "change-this-secret-key-in-production":
            # Allow fallback in dev but warn, or raise if required. Let's raise to be strict on validation.
            if not secret:
                raise RuntimeError("SECRET_KEY environment variable is not set.")

        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        if not jwt_secret:
            raise RuntimeError("JWT_SECRET_KEY environment variable is not set.")

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            print("Gemini API Key Loaded")
        else:
            print("Gemini API Key Missing")
        print(f"Gemini Model: {os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')}")

        print("Environment Validation Passed")

    # =====================================================
    # Gemini AI
    # =====================================================
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    # =====================================================
    # Scraping Configuration
    # =====================================================
    SCRAPING_INTERVAL_HOURS = int(
        os.environ.get("SCRAPING_INTERVAL_HOURS", 6)
    )

    REQUEST_TIMEOUT = int(
        os.environ.get("REQUEST_TIMEOUT", 30)
    )

    USER_AGENT = os.environ.get(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    # =====================================================
    # Real-Time Search
    # =====================================================
    ENABLE_SELENIUM = os.environ.get(
        "ENABLE_SELENIUM",
        "1"
    ) == "1"

    REALTIME_PLATFORM_TIMEOUT_SEC = int(
        os.environ.get("REALTIME_PLATFORM_TIMEOUT_SEC", 60)
    )

    REALTIME_OVERALL_TIMEOUT_SEC = int(
        os.environ.get("REALTIME_OVERALL_TIMEOUT_SEC", 90)
    )

    # =====================================================
    # Recommendation Engine
    # =====================================================
    TFIDF_MAX_FEATURES = int(
        os.environ.get("TFIDF_MAX_FEATURES", 5000)
    )

    SIMILARITY_THRESHOLD = float(
        os.environ.get("SIMILARITY_THRESHOLD", 0.1)
    )

    MAX_RECOMMENDATIONS = int(
        os.environ.get("MAX_RECOMMENDATIONS", 50)
    )

    # =====================================================
    # Product Scoring Weights
    # =====================================================
    PRICE_WEIGHT = float(
        os.environ.get("PRICE_WEIGHT", 0.30)
    )

    RATING_WEIGHT = float(
        os.environ.get("RATING_WEIGHT", 0.30)
    )

    PLATFORM_TRUST_WEIGHT = float(
        os.environ.get("PLATFORM_TRUST_WEIGHT", 0.20)
    )

    REVIEW_COUNT_WEIGHT = float(
        os.environ.get("REVIEW_COUNT_WEIGHT", 0.20)
    )

    # =====================================================
    # Hybrid Recommendation System
    # =====================================================
    HYBRID_CONTENT_WEIGHT = float(
        os.environ.get("HYBRID_CONTENT_WEIGHT", 0.40)
    )

    HYBRID_PREFERENCE_WEIGHT = float(
        os.environ.get("HYBRID_PREFERENCE_WEIGHT", 0.30)
    )

    HYBRID_POPULARITY_WEIGHT = float(
        os.environ.get("HYBRID_POPULARITY_WEIGHT", 0.15)
    )

    HYBRID_RANKING_WEIGHT = float(
        os.environ.get("HYBRID_RANKING_WEIGHT", 0.15)
    )