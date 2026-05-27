import React from 'react';
import './LoadingSpinner.css';

const LoadingSpinner = () => {
  return (
    <div className="loading-overlay">
      <div className="loading-card">
        <div className="spinner"></div>
        <p>Finding the best deals for you...</p>
        <span>Scanning from Amazon, Flipkart, Myntra, and Meesho</span>
      </div>
    </div>
  );
};

export default LoadingSpinner;





