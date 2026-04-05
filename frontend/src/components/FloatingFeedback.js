import React, { useState, useEffect, useRef } from 'react';
import { submitFeedback } from '../services/api';
import './FloatingFeedback.css';

const FloatingFeedback = ({ user, isOpen, onToggle }) => {
  const [rating, setRating] = useState(5);
  const [description, setDescription] = useState('');
  const [name, setName] = useState(user?.name || '');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const feedbackRef = useRef(null);

  useEffect(() => {
    if (user) setName(user.name);
  }, [user]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isOpen && feedbackRef.current && !feedbackRef.current.contains(event.target)) {
        onToggle(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onToggle]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!description.trim()) return;

    setSubmitting(true);
    try {
      await submitFeedback({
        rating,
        description,
        name: user ? user.name : name
      });
      setSubmitted(true);
      setTimeout(() => {
        onToggle(false);
        setSubmitted(false);
        setDescription('');
        setRating(5);
      }, 3000);
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Error submitting feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`floating-feedback-container ${isOpen ? 'active' : ''}`} ref={feedbackRef}>
      {/* Floating Button */}
      <button 
        className={`floating-feedback-fab ${isOpen ? 'hidden' : ''}`} 
        onClick={() => onToggle(true)}
        title="Share Experience"
      >
        <span className="fab-icon">💬</span>
      </button>

      {/* Small Window / Drawer */}
      <div className="feedback-small-window">
        {!user ? (
          <div className="feedback-login-required">
            <div className="lock-icon-mini">🔒</div>
            <h3>Login Required</h3>
            <p>Please log in or register to share your experience with the community.</p>
            <button 
              className="mini-login-btn" 
              onClick={() => {
                onToggle(false);
                // Trigger login panel in App.js (we'll need a way for this)
              }}
            >
              Sign In
            </button>
          </div>
        ) : submitted ? (
          <div className="feedback-success-mini">
            <div className="success-icon-mini">✓</div>
            <h3>Thank You!</h3>
            <p>Your review is posted.</p>
          </div>
        ) : (
          <>
            <div className="feedback-window-header">
              <h3>Share Experience</h3>
              <button className="minimize-btn" onClick={() => onToggle(false)}>—</button>
            </div>
            
            <form onSubmit={handleSubmit} className="feedback-form-mini">
              <div className="mini-form-group">
                <div className="mini-star-rating">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      className={star <= rating ? 'mini-star active' : 'mini-star'}
                      onClick={() => setRating(star)}
                    >
                      ★
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="mini-form-group">
                <textarea
                  placeholder="What can we improve?..."
                  required
                  rows="3"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={300}
                  className="mini-textarea"
                />
                <div className="mini-char-count">{description.length}/300</div>
              </div>
              
              <button 
                type="submit" 
                className="mini-submit-btn" 
                disabled={submitting || !description.trim()}
              >
                {submitting ? 'Sending...' : 'Submit Feedback'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default FloatingFeedback;
