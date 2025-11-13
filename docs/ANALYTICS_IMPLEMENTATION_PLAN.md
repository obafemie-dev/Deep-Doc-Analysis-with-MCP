# Analytics Implementation Plan

## Overview

This document outlines the comprehensive analytics infrastructure for the Deep-Doc-Analysis-with-MCP application. The goal is to track user queries, AI responses, errors, feedback, and performance metrics.

**Status**: Phase 1 - Base Analytics (Session-based tracking)
**Future**: Phase 2 - User Authentication & User-specific Analytics

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Data Collection Strategy](#data-collection-strategy)
4. [Database Schema](#database-schema)
5. [Backend Implementation](#backend-implementation)
6. [Frontend Implementation](#frontend-implementation)
7. [Metrics & Events](#metrics--events)
8. [Dashboard & Visualization](#dashboard--visualization)
9. [Privacy & Compliance](#privacy--compliance)
10. [Migration Path](#migration-path)
11. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         React Frontend                       │
│  - Feedback buttons (thumbs up/down)        │
│  - Analytics event tracking                 │
│  - Session management (UUID)                │
└──────────────┬──────────────────────────────┘
               │ POST /api/v1/analytics/*
               ▼
┌─────────────────────────────────────────────┐
│         FastAPI Backend                      │
│  ┌────────────────────────────────────────┐ │
│  │ Analytics Middleware (async)           │ │
│  │ - Track all requests automatically     │ │
│  │ - Performance monitoring               │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Analytics Service                      │ │
│  │ - Event logging (queries, responses)   │ │
│  │ - Error tracking                       │ │
│  │ - Performance metrics                  │ │
│  │ - Async database writes                │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Analytics API                          │ │
│  │ - POST /api/v1/analytics/event         │ │
│  │ - POST /api/v1/analytics/feedback      │ │
│  │ - GET /api/v1/analytics/summary        │ │
│  └────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────┘
               │ Async writes (zero latency impact)
               ▼
┌─────────────────────────────────────────────┐
│      SQLite Database (analytics.db)          │
│  Tables:                                     │
│  - analytics_events (unified event log)     │
│  - sessions (conversation tracking)         │
│  - query_feedback (thumbs up/down + text)   │
│  - error_logs (detailed error tracking)     │
│                                              │
│  Easy migration to PostgreSQL later         │
└──────────────┬──────────────────────────────┘
               │ SQL connection
               ▼
┌─────────────────────────────────────────────┐
│      Metabase Dashboard (Docker)             │
│  Port: 3000 (configurable)                  │
│  - Visualize usage patterns                 │
│  - Track popular queries                    │
│  - Monitor error rates                      │
│  - Analyze tool usage                       │
│  - Custom dashboards & reports              │
└─────────────────────────────────────────────┘
```

### Design Principles

1. **Performance First**: 100% async analytics - zero impact on API response times
2. **Privacy-Conscious**: Session-based tracking (no PII in Phase 1)
3. **Data Ownership**: All data in your own database (no vendor lock-in)
4. **Scalable**: SQLite → PostgreSQL migration path
5. **Flexible**: Tool-agnostic architecture (switch dashboards anytime)
6. **Comprehensive**: Track everything from queries to errors to performance

---

## Technology Stack

### Backend
- **FastAPI**: Async web framework
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations (optional, for structured schema changes)
- **SQLite**: Initial database (production-ready for millions of rows)
- **PostgreSQL**: Future migration target (when scaling needed)
- **Pydantic**: Data validation for analytics events

### Frontend
- **React 18.3.1**: UI framework
- **Axios**: HTTP client for analytics events
- **UUID**: Session ID generation
- **LocalStorage**: Session persistence

### Dashboard
- **Metabase**: Open-source BI tool
- **Docker**: Container for easy deployment
- **Alternatives**: Grafana, Superset, Redash (easy to swap)

---

## Data Collection Strategy

### Event-Driven Architecture

All user interactions and system events are captured as structured events with:
- **Event Type**: Category (query, response, error, feedback, etc.)
- **Session ID**: Tracks user journey across requests
- **Timestamp**: When the event occurred
- **Data**: Event-specific payload (JSON)
- **Metadata**: Performance metrics, context (JSON)

### Collection Points

#### Backend (Automatic)
- **Middleware**: Intercepts all HTTP requests/responses
- **LLM Service**: Tracks AI interactions, tool usage
- **Error Handlers**: Captures exceptions and failures

#### Frontend (Manual)
- **User Actions**: Button clicks, file uploads
- **Feedback**: Thumbs up/down, comments
- **Session Events**: Start, end, idle time

### Async Processing

```python
# Non-blocking event logging
async def track_event(event_type: str, data: dict):
    """Log event asynchronously without blocking request"""
    asyncio.create_task(
        analytics_service.log_event(event_type, data)
    )
```

---

## Database Schema

### 1. analytics_events

**Purpose**: Unified event log for all analytics data

```sql
CREATE TABLE analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,           -- 'query', 'response', 'error', 'upload', 'tool_call', etc.
    session_id TEXT NOT NULL,           -- UUID for session tracking
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    data JSON,                          -- Event-specific data (flexible schema)
    metadata JSON,                      -- Performance metrics, context, browser info

    INDEX idx_session_id (session_id),
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp)
);
```

**Example Event - Query**:
```json
{
  "id": 12345,
  "event_type": "query",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-13T10:30:45Z",
  "data": {
    "query_text": "What's the average sales by region?",
    "file_path": "/uploads/sales_data.xlsx",
    "conversation_turn": 3,
    "llm_provider": "claude"
  },
  "metadata": {
    "endpoint": "/api/v1/chat/stream",
    "user_agent": "Mozilla/5.0..."
  }
}
```

**Example Event - Response**:
```json
{
  "id": 12346,
  "event_type": "response",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-13T10:30:52Z",
  "data": {
    "query_id": 12345,
    "response_text": "Based on the analysis...",
    "response_length": 450,
    "tool_calls": [
      {"tool": "query_excel_data", "duration_ms": 234},
      {"tool": "analyze_excel_data", "duration_ms": 156}
    ],
    "streaming": true,
    "success": true
  },
  "metadata": {
    "total_duration_ms": 7200,
    "time_to_first_token_ms": 890,
    "tokens_estimated": 120
  }
}
```

### 2. sessions

**Purpose**: Track conversation sessions and engagement

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                -- UUID
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    last_activity_at DATETIME,
    message_count INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    llm_provider TEXT,                  -- 'ollama' or 'claude'
    total_query_time_ms INTEGER DEFAULT 0,

    INDEX idx_started_at (started_at)
);
```

### 3. query_feedback

**Purpose**: Store user feedback on AI responses

```sql
CREATE TABLE query_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,           -- Frontend message ID
    query_event_id INTEGER,             -- Links to analytics_events
    rating INTEGER NOT NULL,            -- 1 (thumbs up), -1 (thumbs down)
    comment TEXT,                       -- Optional user comment
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (query_event_id) REFERENCES analytics_events(id),
    INDEX idx_session_id (session_id),
    INDEX idx_rating (rating)
);
```

### 4. error_logs

**Purpose**: Detailed error tracking and debugging

```sql
CREATE TABLE error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    error_type TEXT NOT NULL,           -- Exception class name
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    endpoint TEXT,
    request_data JSON,                  -- Request body, params
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_session_id (session_id),
    INDEX idx_error_type (error_type),
    INDEX idx_timestamp (timestamp)
);
```

---

## Backend Implementation

### File Structure

```
backend/app/
├── models/
│   └── analytics.py              # SQLAlchemy models for analytics tables
├── services/
│   └── analytics_service.py      # Analytics business logic
├── middleware/
│   └── analytics_middleware.py   # Automatic request/response tracking
├── routers/
│   └── analytics.py              # API endpoints for analytics
├── schemas/
│   └── analytics.py              # Pydantic schemas for validation
├── database.py                   # Add analytics DB connection
└── main.py                       # Register middleware and router
```

### Key Components

#### 1. Analytics Models (`models/analytics.py`)

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    data = Column(JSON)
    metadata = Column(JSON)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    started_at = Column(DateTime, server_default=func.now(), index=True)
    ended_at = Column(DateTime)
    last_activity_at = Column(DateTime)
    message_count = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    llm_provider = Column(String)
    total_query_time_ms = Column(Integer, default=0)

class QueryFeedback(Base):
    __tablename__ = "query_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    message_id = Column(String, nullable=False)
    query_event_id = Column(Integer, ForeignKey("analytics_events.id"))
    rating = Column(Integer, nullable=False, index=True)
    comment = Column(Text)
    timestamp = Column(DateTime, server_default=func.now())

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    error_type = Column(String, nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    endpoint = Column(String)
    request_data = Column(JSON)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
```

#### 2. Analytics Service (`services/analytics_service.py`)

```python
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import AnalyticsEvent, Session, ErrorLog
import asyncio

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: str,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an analytics event asynchronously"""
        event = AnalyticsEvent(
            event_type=event_type,
            session_id=session_id,
            data=data or {},
            metadata=metadata or {}
        )
        self.db.add(event)
        await self.db.commit()
        return event

    async def track_query(
        self,
        session_id: str,
        query_text: str,
        file_path: Optional[str],
        conversation_turn: int,
        llm_provider: str
    ):
        """Track a user query"""
        return await self.log_event(
            event_type="query",
            session_id=session_id,
            data={
                "query_text": query_text,
                "file_path": file_path,
                "conversation_turn": conversation_turn,
                "llm_provider": llm_provider
            }
        )

    async def track_response(
        self,
        session_id: str,
        query_id: int,
        response_text: str,
        tool_calls: list,
        duration_ms: int,
        success: bool
    ):
        """Track an AI response"""
        return await self.log_event(
            event_type="response",
            session_id=session_id,
            data={
                "query_id": query_id,
                "response_text": response_text,
                "response_length": len(response_text),
                "tool_calls": tool_calls,
                "success": success
            },
            metadata={
                "total_duration_ms": duration_ms
            }
        )

    async def log_error(
        self,
        session_id: Optional[str],
        error_type: str,
        error_message: str,
        stack_trace: Optional[str],
        endpoint: Optional[str],
        request_data: Optional[Dict]
    ):
        """Log an error"""
        error_log = ErrorLog(
            session_id=session_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            request_data=request_data
        )
        self.db.add(error_log)
        await self.db.commit()
        return error_log
```

#### 3. Analytics Middleware (`middleware/analytics_middleware.py`)

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.services.analytics_service import AnalyticsService

class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Extract session ID from headers
        session_id = request.headers.get("X-Session-ID")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log API request (async, non-blocking)
        if session_id:
            # Don't block the response
            asyncio.create_task(
                self._log_request(
                    request.url.path,
                    request.method,
                    session_id,
                    response.status_code,
                    duration_ms
                )
            )

        return response

    async def _log_request(self, path, method, session_id, status_code, duration_ms):
        # Implementation here
        pass
```

#### 4. Analytics Router (`routers/analytics.py`)

```python
from fastapi import APIRouter, Depends
from app.schemas.analytics import FeedbackRequest, EventRequest
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.post("/event")
async def track_event(
    event: EventRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """Track a custom analytics event from frontend"""
    await analytics.log_event(
        event_type=event.event_type,
        session_id=event.session_id,
        data=event.data,
        metadata=event.metadata
    )
    return {"status": "success"}

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """Submit user feedback on AI response"""
    # Implementation here
    return {"status": "success"}
```

---

## Frontend Implementation

### File Structure

```
frontend/src/
├── components/
│   ├── FeedbackButtons.jsx       # Thumbs up/down UI
│   ├── MessageList.jsx           # Modified to include feedback
│   └── ChatInterface.jsx         # Modified for analytics tracking
├── hooks/
│   └── useAnalytics.js           # Analytics tracking hook
├── contexts/
│   └── SessionContext.jsx        # Session management
└── utils/
    └── analytics.js              # Analytics helpers
```

### Key Components

#### 1. Session Context (`contexts/SessionContext.jsx`)

```javascript
import React, { createContext, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

export const SessionContext = createContext();

export const SessionProvider = ({ children }) => {
  const [sessionId, setSessionId] = useState(() => {
    // Get existing session or create new one
    const existing = localStorage.getItem('analytics_session_id');
    if (existing) return existing;

    const newId = uuidv4();
    localStorage.setItem('analytics_session_id', newId);
    return newId;
  });

  return (
    <SessionContext.Provider value={{ sessionId }}>
      {children}
    </SessionContext.Provider>
  );
};
```

#### 2. Analytics Hook (`hooks/useAnalytics.js`)

```javascript
import { useContext } from 'react';
import { SessionContext } from '../contexts/SessionContext';
import axios from 'axios';

export const useAnalytics = () => {
  const { sessionId } = useContext(SessionContext);

  const trackEvent = async (eventType, data, metadata = {}) => {
    try {
      await axios.post('/api/v1/analytics/event', {
        event_type: eventType,
        session_id: sessionId,
        data,
        metadata
      }, {
        headers: {
          'X-Session-ID': sessionId
        }
      });
    } catch (error) {
      console.error('Analytics tracking failed:', error);
      // Fail silently - don't disrupt user experience
    }
  };

  return { trackEvent, sessionId };
};
```

#### 3. Feedback Buttons (`components/FeedbackButtons.jsx`)

```javascript
import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { useAnalytics } from '../hooks/useAnalytics';

const FeedbackButtons = ({ messageId, queryEventId }) => {
  const [rating, setRating] = useState(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState('');
  const { sessionId } = useAnalytics();

  const handleFeedback = async (value) => {
    setRating(value);

    // Submit feedback
    await fetch('/api/v1/analytics/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
      },
      body: JSON.stringify({
        message_id: messageId,
        query_event_id: queryEventId,
        rating: value,
        comment: comment || null
      })
    });
  };

  return (
    <div className="flex items-center gap-2 mt-2">
      <button
        onClick={() => handleFeedback(1)}
        className={`p-1 rounded ${rating === 1 ? 'bg-green-100' : ''}`}
        title="Helpful"
      >
        <ThumbsUp size={16} />
      </button>
      <button
        onClick={() => handleFeedback(-1)}
        className={`p-1 rounded ${rating === -1 ? 'bg-red-100' : ''}`}
        title="Not helpful"
      >
        <ThumbsDown size={16} />
      </button>
    </div>
  );
};

export default FeedbackButtons;
```

---

## Metrics & Events

### Event Types

| Event Type | Description | Data Tracked |
|------------|-------------|--------------|
| `query` | User asks a question | Query text, file path, conversation turn, LLM provider |
| `response` | AI generates response | Response text, tool calls, duration, success status |
| `error` | System error occurs | Error type, message, stack trace, context |
| `upload` | File uploaded | Filename, size, type, processing time |
| `tool_call` | MCP tool executed | Tool name, parameters, execution time, result |
| `feedback` | User rates response | Rating (1/-1), optional comment |
| `session_start` | Session begins | Timestamp, user agent |
| `session_end` | Session ends | Duration, message count |
| `clear_chat` | User clears conversation | Message count before clear |

### Performance Metrics

- **Time to First Token (TTFT)**: Time from query to first response chunk
- **Total Response Time**: Complete query → response duration
- **Tool Execution Time**: Individual tool performance
- **API Latency**: Endpoint response times
- **Upload Processing Time**: File parsing duration

### Engagement Metrics

- **Messages per Session**: Conversation depth
- **Session Duration**: Active time
- **Tool Usage Distribution**: Which tools are most popular
- **Feedback Rate**: % of responses rated
- **Positive Feedback Rate**: % thumbs up
- **Error Rate**: Errors per session

---

## Dashboard & Visualization

### Metabase Setup

```bash
# 1. Start Metabase container
docker run -d \
  --name metabase \
  -p 3000:3000 \
  -v metabase-data:/metabase-data \
  metabase/metabase

# 2. Access Metabase at http://localhost:3000

# 3. Connect to SQLite database
# Database type: SQLite
# Database file: /path/to/analytics.db

# 4. Start building dashboards!
```

### Recommended Dashboards

#### 1. **Overview Dashboard**
- Total sessions (today, week, month)
- Total queries
- Average response time
- Error rate
- Positive feedback rate

#### 2. **Usage Dashboard**
- Queries over time (line chart)
- Tool usage distribution (pie chart)
- Files uploaded per day (bar chart)
- LLM provider split (Ollama vs Claude)

#### 3. **Performance Dashboard**
- Average response time by endpoint
- Tool execution times (comparison)
- Time to first token trend
- Slow queries (>5s response time)

#### 4. **Quality Dashboard**
- Feedback ratings over time
- Most helpful responses (high ratings)
- Most problematic queries (low ratings)
- Error types distribution

#### 5. **User Engagement**
- Session duration distribution
- Messages per session
- Returning sessions rate
- Peak usage hours

### SQL Query Examples

```sql
-- Top 10 most common queries
SELECT
  json_extract(data, '$.query_text') as query,
  COUNT(*) as count
FROM analytics_events
WHERE event_type = 'query'
GROUP BY query
ORDER BY count DESC
LIMIT 10;

-- Average response time by tool
SELECT
  json_extract(tool_call, '$.tool') as tool_name,
  AVG(CAST(json_extract(tool_call, '$.duration_ms') AS INTEGER)) as avg_duration_ms
FROM analytics_events,
  json_each(json_extract(data, '$.tool_calls')) as tool_call
WHERE event_type = 'response'
GROUP BY tool_name
ORDER BY avg_duration_ms DESC;

-- Feedback satisfaction rate
SELECT
  SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as satisfaction_rate
FROM query_feedback;

-- Error rate by endpoint
SELECT
  endpoint,
  COUNT(*) as error_count,
  DATE(timestamp) as date
FROM error_logs
GROUP BY endpoint, date
ORDER BY date DESC, error_count DESC;
```

---

## Privacy & Compliance

### Current Approach (Phase 1)

- **Session-based tracking**: No user identification
- **UUID sessions**: Anonymous, stored in browser localStorage
- **No PII collected**: No names, emails, IP addresses
- **Data stored locally**: Your own database, your control

### GDPR Considerations

If deploying in EU or collecting user data in Phase 2:

1. **Data Minimization**: Only collect necessary data
2. **Consent**: Inform users about analytics
3. **Right to Access**: Provide analytics data on request
4. **Right to Deletion**: Ability to delete session data
5. **Data Retention**: Set retention policies (e.g., 90 days)

### Implementation for GDPR

```sql
-- Add retention policy (run as scheduled job)
DELETE FROM analytics_events
WHERE timestamp < datetime('now', '-90 days');

-- Delete specific session data
DELETE FROM analytics_events WHERE session_id = ?;
DELETE FROM sessions WHERE id = ?;
DELETE FROM query_feedback WHERE session_id = ?;
DELETE FROM error_logs WHERE session_id = ?;
```

---

## Migration Path

### SQLite → PostgreSQL Migration

When scaling beyond SQLite (typically >100GB data or high concurrency):

```bash
# 1. Install pgloader
apt-get install pgloader

# 2. Migrate data
pgloader sqlite:///path/to/analytics.db postgresql://user:pass@localhost/analytics

# 3. Update database connection in FastAPI
# database.py
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost/analytics"
```

### Dashboard Migration (Easy!)

**Your analytics infrastructure is dashboard-agnostic**. To switch:

```bash
# Stop Metabase
docker stop metabase

# Option 1: Apache Superset
docker run -d -p 8088:8088 apache/superset

# Option 2: Grafana
docker run -d -p 3000:3000 grafana/grafana

# Option 3: Redash
docker run -d -p 5000:5000 redash/redash

# Option 4: Build custom React dashboard
# Your data is already available via API
```

**No code changes needed** - just connect the new tool to `analytics.db`.

---

## Future Enhancements

### Phase 2: User Authentication

When adding sign-in:

1. **Add user_id column** to sessions table
2. **Link sessions to users**
3. **Track user-specific metrics**:
   - Unique users (DAU, WAU, MAU)
   - User retention rate
   - Power users (top 10%)
   - New vs returning users

4. **Per-user analytics**:
   - User dashboard (their own stats)
   - Usage history
   - Favorite tools
   - Average session duration

### Advanced Features

- **A/B Testing**: Test different LLM prompts, UI variations
- **Anomaly Detection**: Alert on unusual error rates, slow queries
- **Predictive Analytics**: Forecast usage, capacity planning
- **Real-time Dashboard**: WebSocket updates for live monitoring
- **Export API**: Download analytics data (CSV, JSON)
- **Alerts**: Email/Slack notifications for errors, milestones

### OpenTelemetry Integration

For enterprise-grade observability:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Instrument FastAPI automatically
FastAPIInstrumentor.instrument_app(app)

# Traces, metrics, and logs in one place
# Compatible with Grafana, Datadog, New Relic
```

---

## Summary

### What We're Building

✅ **Backend**:
- SQLite database with 4 tables
- Analytics middleware (automatic tracking)
- Analytics service (event logging)
- Feedback API endpoints

✅ **Frontend**:
- Session management (UUID)
- Feedback buttons (thumbs up/down)
- Analytics tracking hook
- Event tracking on key actions

✅ **Dashboard**:
- Metabase for visualization
- Pre-built dashboards for common queries
- Easy migration to other tools

### Key Benefits

- **Zero performance impact**: 100% async
- **Complete data ownership**: Your database
- **Easy to extend**: Event-driven architecture
- **Privacy-first**: Session-based, no PII
- **Scalable**: SQLite → PostgreSQL path
- **Tool-agnostic**: Switch dashboards anytime

### Next Steps

1. Research best coding practices ✅
2. Implement backend infrastructure
3. Build frontend components
4. Test thoroughly
5. Deploy Metabase
6. Create initial dashboards

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Author**: Claude (AI Assistant)
**Status**: Ready for Implementation
