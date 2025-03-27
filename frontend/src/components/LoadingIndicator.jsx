// File: components/LoadingIndicator.jsx
import React from 'react';

function LoadingIndicator() {
  return (
    <div className="loading-indicator">
      <div className="spinner"></div>
      <p>Searching across multiple sources...</p>
    </div>
  );
}

export default LoadingIndicator;