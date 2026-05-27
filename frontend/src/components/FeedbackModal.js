import React, { useState } from 'react';
import { submitFeedback } from '../services/api';
import './FeedbackModal.css';

const FeedbackModal = ({ isOpen, onClose, user }) => {
  const [rating, setRating] = useState(5);
  const [description, setDescription] = useState('');
  const [name, setName] = useState(user?.name || '');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

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
        onClose();
        setSubmitted(false);
        setDescription('');
      }, 2000);
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Error submitting feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="feedback-modal-overlay" onClick={onClose}>
      <div className="feedback-modal-card" onClick={(e) => e.stopPropagation()}>
        {submitted ? (
          <div className="feedback-success">
            <div className="success-icon">✓</div>
            <h2>Thank You!</h2>
            <p>Your feedback helps us make BuySmart better for everyone.</p>
          </div>
        ) : (
          <>
            <div className="feedback-modal-header">
              <h2>Share Your Experience</h2>
              <button className="close-btn" onClick={onClose}>×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="feedback-form">
              {!user && (
                <div className="form-group">
                  <label>Your Name (Optional)</label>
                  <input
                    type="text"
                    placeholder="Enter your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              )}
              
              <div className="form-group">
                <label>Overall Rating</label>
                <div className="star-rating-input">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      className={star <= rating ? 'star active' : 'star'}
                      onClick={() => setRating(star)}
                    >
                      ★
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="form-group">
                <label>What do you think of BuySmart?</label>
                <textarea
                  placeholder="Share your thoughts, suggestions, or issues..."
                  required
                  rows="4"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={500}
                />
                <div className="char-count">{description.length}/500</div>
              </div>
              
              <button 
                type="submit" 
                className="submit-feedback-btn" 
                disabled={submitting || !description.trim()}
              >
                {submitting ? 'Submitting...' : 'Post Review'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default FeedbackModal;
