import React from 'react';

const SuggestedQueries = ({ queries, onSelectQuery }) => {
  if (!queries || queries.length === 0) return null;

  return (
    <div className="suggested-queries-card glass-card">
      <span className="suggested-label">Suggested Searches:</span>
      <div className="queries-list">
        {queries.map((q, idx) => (
          <button 
            key={idx} 
            className="query-bubble"
            onClick={() => onSelectQuery(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQueries;
