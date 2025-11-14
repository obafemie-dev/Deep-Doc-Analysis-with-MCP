/**
 * Feedback Buttons Component
 *
 * Provides thumbs up/down buttons for users to rate AI responses.
 */
import React, { useState } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';

const FeedbackButtons = ({ messageId, queryEventId = null }) => {
  const [rating, setRating] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { submitFeedback } = useAnalytics();

  const handleFeedback = async (value) => {
    if (isSubmitting || rating !== null) return; // Prevent double submission

    setIsSubmitting(true);
    setRating(value);

    try {
      await submitFeedback(messageId, value, null, queryEventId);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Reset on error
      setRating(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-2 mt-2">
      <span className="text-xs text-gray-500">Was this helpful?</span>

      <button
        onClick={() => handleFeedback(1)}
        disabled={rating !== null}
        className={`p-1 rounded transition-colors ${
          rating === 1
            ? 'bg-green-100 text-green-700'
            : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
        } ${rating !== null && rating !== 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
        title="Helpful"
        aria-label="Thumbs up"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill={rating === 1 ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>
      </button>

      <button
        onClick={() => handleFeedback(-1)}
        disabled={rating !== null}
        className={`p-1 rounded transition-colors ${
          rating === -1
            ? 'bg-red-100 text-red-700'
            : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
        } ${rating !== null && rating !== -1 ? 'opacity-50 cursor-not-allowed' : ''}`}
        title="Not helpful"
        aria-label="Thumbs down"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill={rating === -1 ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
        </svg>
      </button>

      {rating !== null && (
        <span className="text-xs text-gray-500 ml-1">
          Thanks for your feedback!
        </span>
      )}
    </div>
  );
};

export default FeedbackButtons;
