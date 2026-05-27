import React from 'react';
import './NotificationTicker.css';

const NotificationTicker = () => {
    const alerts = [
        {
            icon: "🔍",
            label: "Compare Prices:",
            text: "Instantly check Amazon, Flipkart, Myntra, and Meesho to find the lowest price."
        },
        {
            icon: "⚡",
            label: "Fast Scan:",
            text: "Searches multiple stores at the same time to show you the latest deals."
        },
        {
            icon: "🛡️",
            label: "Shop Safe:",
            text: "Get direct, verified links to buy safely from official store pages."
        },
        {
            icon: "⭐",
            label: "Top Picks:",
            text: "Discover highly-rated products selected for true value and quality."
        },
        {
            icon: "🎁",
            label: "100% Free:",
            text: "BuySmart helps you shop smart without any ads or hidden fees."
        }
    ];

    return (
        <div className="ticker-container">
            <div className="ticker-wrapper">
                <div className="ticker-content">
                    {alerts.map((alert, index) => (
                        <div key={index} className="ticker-item">
                            <span className="ticker-icon">{alert.icon}</span>
                            <span className="ticker-label-text">{alert.label}</span>
                            <span className="ticker-desc">{alert.text}</span>
                            <span className="ticker-separator">✦</span>
                        </div>
                    ))}
                    {/* Duplicate for seamless loop */}
                    {alerts.map((alert, index) => (
                        <div key={`dup-${index}`} className="ticker-item">
                            <span className="ticker-icon">{alert.icon}</span>
                            <span className="ticker-label-text">{alert.label}</span>
                            <span className="ticker-desc">{alert.text}</span>
                            <span className="ticker-separator">✦</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default NotificationTicker;
