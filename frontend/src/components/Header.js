import React from 'react';
import './Header.css';

const Header = () => {
  return (
    <header className="app-header">
      <h1>BuySmart</h1>
      {/* The subtitle was moved to App.js or another component.
          This header now contains only the main title. */}
    </header>
  );
};

export default Header;
