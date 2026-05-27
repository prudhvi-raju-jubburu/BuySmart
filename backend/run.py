"""
Simple script to run the Flask application
"""
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Buy Smart - Product Recommendation System (Backend)")
    print("=" * 60)
    print("\nStarting server...")
    print("API: http://localhost:5001/api/")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)





