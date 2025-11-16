/**
 * Session Context for Analytics
 *
 * Manages session ID for analytics tracking across the application.
 * Session ID is persisted in localStorage and sent with all API requests.
 */
import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { API_ENDPOINTS } from '../config/api';

// Generate UUID v4
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

const SessionContext = createContext(null);

export const SessionProvider = ({ children }) => {
  const [sessionId, setSessionId] = useState(() => {
    // Get existing session ID from localStorage or create new one
    const existing = localStorage.getItem('analytics_session_id');
    if (existing) {
      return existing;
    }

    const newId = generateUUID();
    localStorage.setItem('analytics_session_id', newId);
    return newId;
  });

  const [sessionStarted, setSessionStarted] = useState(false);

  // Memoize initSession to prevent re-creation on every render
  const initSession = useCallback(async () => {
    try {
      await fetch(API_ENDPOINTS.ANALYTICS_SESSION_START, {
        method: 'POST',
        credentials: 'include',  // Send auth cookies for user tracking
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          session_id: sessionId,
          llm_provider: 'claude'  // Will be dynamic later
        })
      });

      setSessionStarted(true);
      console.log('Analytics session started:', sessionId);
    } catch (error) {
      console.error('Failed to start analytics session:', error);
    }
  }, [sessionId]);

  // End session when user closes tab/window
  const endSession = useCallback(async () => {
    try {
      // Use sendBeacon for reliable delivery even during page unload
      const endpoint = API_ENDPOINTS.ANALYTICS_SESSION_END;
      const blob = new Blob([JSON.stringify({ session_id: sessionId })], {
        type: 'application/json'
      });

      // sendBeacon returns false if queueing failed
      if (!navigator.sendBeacon) {
        // Fallback to fetch with keepalive flag for older browsers
        await fetch(endpoint, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
          },
          body: JSON.stringify({ session_id: sessionId }),
          keepalive: true  // Ensures request completes even after page closes
        });
      } else {
        navigator.sendBeacon(endpoint, blob);
      }

      console.log('Analytics session ended:', sessionId);
    } catch (error) {
      console.error('Failed to end analytics session:', error);
    }
  }, [sessionId]);

  // Initialize session on mount
  useEffect(() => {
    if (!sessionStarted) {
      initSession();
    }
  }, [sessionStarted, initSession]);

  // Cleanup: end session on page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      endSession();
    };

    // Listen for page unload (browser close, tab close, navigation away)
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Cleanup on component unmount (when SessionProvider is destroyed)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Also end session when provider unmounts (app closed)
      endSession();
    };
  }, [endSession]);

  const resetSession = () => {
    const newId = generateUUID();
    localStorage.setItem('analytics_session_id', newId);
    setSessionId(newId);
    setSessionStarted(false);
  };

  const value = {
    sessionId,
    resetSession,
    endSession  // Expose for manual session ending if needed
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};

// Custom hook to use session context
export const useSession = () => {
  const context = useContext(SessionContext);

  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }

  return context;
};

export default SessionContext;
