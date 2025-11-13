/**
 * Session Context for Analytics
 *
 * Manages session ID for analytics tracking across the application.
 * Session ID is persisted in localStorage and sent with all API requests.
 */
import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';

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
      await fetch('/api/v1/analytics/session/start', {
        method: 'POST',
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

  // Initialize session on mount
  useEffect(() => {
    if (!sessionStarted) {
      initSession();
    }
  }, [sessionStarted, initSession]);

  const resetSession = () => {
    const newId = generateUUID();
    localStorage.setItem('analytics_session_id', newId);
    setSessionId(newId);
    setSessionStarted(false);
  };

  const value = {
    sessionId,
    resetSession
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
