/**
 * Analytics Hook
 *
 * Custom hook for tracking analytics events from React components.
 * Automatically includes session ID in all requests.
 */
import { useCallback } from 'react';
import { useSession } from '../contexts/SessionContext';

export const useAnalytics = () => {
  const { sessionId } = useSession();

  /**
   * Track a custom event
   *
   * @param {string} eventType - Type of event (query, response, upload, etc.)
   * @param {object} data - Event-specific data
   * @param {object} metadata - Performance metrics, context
   */
  const trackEvent = useCallback(async (eventType, data = {}, metadata = {}) => {
    try {
      await fetch('/api/v1/analytics/event', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          event_type: eventType,
          session_id: sessionId,
          data,
          metadata
        })
      });
    } catch (error) {
      // Fail silently - don't disrupt user experience
      console.error('Analytics tracking failed:', error);
    }
  }, [sessionId]);

  /**
   * Submit user feedback on an AI response
   *
   * @param {string} messageId - Frontend message ID
   * @param {number} rating - 1 (thumbs up) or -1 (thumbs down)
   * @param {string} comment - Optional comment
   * @param {number} queryEventId - Optional query event ID
   */
  const submitFeedback = useCallback(async (messageId, rating, comment = null, queryEventId = null) => {
    try {
      const response = await fetch('/api/v1/analytics/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          message_id: messageId,
          session_id: sessionId,
          rating,
          comment,
          query_event_id: queryEventId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      throw error;
    }
  }, [sessionId]);

  /**
   * Track file upload
   *
   * @param {string} filename - Name of uploaded file
   * @param {number} fileSize - File size in bytes
   * @param {string} fileType - File extension
   * @param {number} processingTime - Upload processing time in ms
   */
  const trackFileUpload = useCallback(async (filename, fileSize, fileType, processingTime) => {
    await trackEvent('upload', {
      filename,
      file_size: fileSize,
      file_type: fileType
    }, {
      processing_time_ms: processingTime
    });
  }, [trackEvent]);

  /**
   * Track user query
   *
   * @param {string} queryText - The user's question
   * @param {string} filePath - Path to the Excel file (if any)
   * @param {number} conversationTurn - Turn number in conversation
   */
  const trackQuery = useCallback(async (queryText, filePath = null, conversationTurn = 1) => {
    await trackEvent('query', {
      query_text: queryText,
      file_path: filePath,
      conversation_turn: conversationTurn
    });
  }, [trackEvent]);

  /**
   * Track AI response
   *
   * @param {string} responseText - The AI's response
   * @param {array} toolCalls - Tools used during response
   * @param {number} duration - Response time in ms
   * @param {boolean} success - Whether response succeeded
   */
  const trackResponse = useCallback(async (responseText, toolCalls = [], duration = 0, success = true) => {
    await trackEvent('response', {
      response_text: responseText.substring(0, 500),
      tool_calls: toolCalls,
      success
    }, {
      total_duration_ms: duration
    });
  }, [trackEvent]);

  /**
   * Track clear chat event
   *
   * @param {number} messageCount - Number of messages before clearing
   */
  const trackClearChat = useCallback(async (messageCount) => {
    await trackEvent('clear_chat', {
      message_count: messageCount
    });
  }, [trackEvent]);

  return {
    sessionId,
    trackEvent,
    submitFeedback,
    trackFileUpload,
    trackQuery,
    trackResponse,
    trackClearChat
  };
};

export default useAnalytics;
