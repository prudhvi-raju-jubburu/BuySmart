import React from 'react';
import './NotificationTicker.css';

const NotificationTicker = () => {
    const alerts = [
        "🚀 Live Status: Scanners active across Amazon, Flipkart, Myntra & Meesho.",
        "📊 Accuracy: 99.8% real-time price matching verified by BuySmart engine.",
        "📦 Fast Mode: Multi-threaded scraping delivers results in under 15 seconds.",
        "✨ New: AI-powered product recommendations now available!"
    ];

    return (
        <div className="ticker-container">
            {/* <div className="ticker-label"></div> */}
            <div className="ticker-wrapper">
                <div className="ticker-content">
                    {alerts.map((alert, index) => (
                        <span key={index} className="ticker-item">{alert}</span>
                    ))}
                    {/* Duplicate for seamless loop */}
                    {alerts.map((alert, index) => (
                        <span key={`dup-${index}`} className="ticker-item">{alert}</span>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default NotificationTicker;
