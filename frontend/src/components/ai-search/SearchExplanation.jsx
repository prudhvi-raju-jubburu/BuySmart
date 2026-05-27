import React, { useState } from 'react';

const getBulletMeta = (bullet) => {
  const b = bullet.toLowerCase();
  if (b.includes('budget') || b.includes('price') || b.includes('₹') || b.includes('under') || b.includes('below') || b.includes('limit')) {
    return { icon: '💰', className: 'bullet-budget' };
  }
  if (b.includes('category') || b.includes('laptop') || b.includes('phone') || b.includes('shoe') || b.includes('watch') || b.includes('headphone')) {
    return { icon: '🏷️', className: 'bullet-category' };
  }
  if (b.includes('coding') || b.includes('gaming') || b.includes('machine learning') || b.includes('purpose') || b.includes('use case')) {
    return { icon: '🎯', className: 'bullet-purpose' };
  }
  if (b.includes('brand') || b.includes('samsung') || b.includes('apple') || b.includes('lenovo') || b.includes('dell') || b.includes('hp') || b.includes('nike')) {
    return { icon: '🏢', className: 'bullet-brand' };
  }
  if (b.includes('rating') || b.includes('review') || b.includes('star')) {
    return { icon: '⭐', className: 'bullet-rating' };
  }
  return { icon: '✅', className: 'bullet-default' };
};

const SearchExplanation = ({ eventId, bullets, initialExplanation, onSubmitFeedback }) => {
  const [feedback, setFeedback] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFeedback = async (type) => {
    if (isSubmitting || feedback) return;
    setIsSubmitting(true);
    try {
      await onSubmitFeedback(eventId, type);
      setFeedback(type);
    } catch (e) {
      console.error("Error submitting feedback:", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const rawBullets = bullets && bullets.length > 0
    ? bullets
    : (initialExplanation ? initialExplanation.split(' | ') : []);

  const meaningfulBullets = rawBullets.filter(b => b && b.trim().length > 3);

  return (
    <div className="explanation-card glass-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span style={{ fontSize: '1.1rem' }}>🔍</span>
        <h3>How We Searched</h3>
      </div>

      {meaningfulBullets.length > 0 ? (
        <ul className="explanation-bullets">
          {meaningfulBullets.map((bullet, idx) => {
            const cleanBullet = bullet.startsWith('✓ ') ? bullet.substring(2) : bullet;
            const { icon, className } = getBulletMeta(cleanBullet);
            return (
              <li key={idx} className={`explanation-bullet-item ${className}`}>
                <span className="bullet-icon">{icon}</span>
                <span className="bullet-text">{cleanBullet}</span>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="explanation-empty-state">
          <div style={{ fontSize: '1.8rem', marginBottom: '0.4rem' }}>🔍</div>
          <p>
            We found products matching your search. Try something like{' '}
            <em className="example-query">"laptops for coding under ₹60,000"</em>{' '}
            for detailed filtering.
          </p>
        </div>
      )}

      {eventId && (
        <div className="feedback-section">
          <span className="feedback-text">Were these results helpful?</span>
          <div className="feedback-buttons">
            <button
              className={`feedback-btn ${feedback === 'helpful' ? 'active helpful' : ''}`}
              onClick={() => handleFeedback('helpful')}
              disabled={isSubmitting || !!feedback}
            >
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
              </svg>
              {feedback === 'helpful' ? 'Marked!' : 'Yes'}
            </button>
            <button
              className={`feedback-btn ${feedback === 'not_helpful' ? 'active not-helpful' : ''}`}
              onClick={() => handleFeedback('not_helpful')}
              disabled={isSubmitting || !!feedback}
            >
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
              </svg>
              {feedback === 'not_helpful' ? 'Noted!' : 'No'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchExplanation;
