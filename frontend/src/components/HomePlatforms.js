import React from 'react';
import './HomePlatforms.css';

const PlatformCard = ({ name, subtitle, color, url }) => {
  return (
    <a className="platform-card" href={url} target="_blank" rel="noopener noreferrer" style={{ borderColor: color }}>
      <div className="platform-badge" style={{ background: color }}>{name}</div>
      <div className="platform-sub">{subtitle}</div>
      <div className="platform-cta">Open →</div>
    </a>
  );
};

const HomePlatforms = () => {
  return (
    <div className="home-platforms" id="home">
      <div className="home-title">Compare across platforms</div>
      <div className="home-subtitle">Amazon • Flipkart • Meesho • Myntra </div>
      <div className="platform-grid">
        <PlatformCard name="Amazon" subtitle="Wide catalog + fast delivery" color="#f59e0b" url="https://www.amazon.in/" />
        <PlatformCard name="Flipkart" subtitle="Great deals in India" color="#2563eb" url="https://www.flipkart.com/" />
        <PlatformCard name="Meesho" subtitle="Budget-friendly items" color="#db2777" url="https://www.meesho.com/" />
        <PlatformCard name="Myntra" subtitle="Fashion + lifestyle" color="#111827" url="https://www.myntra.com/" />
      </div>
    </div>
  );
};

export default HomePlatforms;





