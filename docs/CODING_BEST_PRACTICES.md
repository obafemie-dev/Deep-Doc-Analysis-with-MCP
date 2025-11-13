# Coding Best Practices for Analytics Implementation

## Overview

This document outlines the best practices we'll follow when implementing the analytics infrastructure based on 2025 industry standards for FastAPI, React, and SQLAlchemy.

---

## FastAPI Best Practices

### 1. Project Structure (Domain-Driven Design)

Organize code by business domain rather than technical layers:

```
backend/app/
├── models/          # SQLAlchemy models
│   └── analytics.py
├── schemas/         # Pydantic models (request/response validation)
│   └── analytics.py
├── services/        # Business logic
│   └── analytics_service.py
├── routers/         # API endpoints
│   └── analytics.py
└── middleware/      # Cross-cutting concerns
    └── analytics_middleware.py
```

### 2. Async/Await Guidelines

**Rule**: If using `async def`, only perform non-blocking I/O operations.

```python
# ✅ GOOD: Async route with async operations
@router.post("/event")
async def track_event(event: EventRequest, db: AsyncSession = Depends(get_db)):
    await analytics_service.log_event(db, event)
    return {"status": "success"}

# ❌ BAD: Async route with blocking operations
@router.post("/event")
async def track_event(event: EventRequest):
    time.sleep(1)  # BLOCKS THE EVENT LOOP!
    return {"status": "success"}

# ✅ GOOD: Sync route for blocking operations (runs in threadpool)
@router.post("/blocking-task")
def blocking_task():
    time.sleep(1)  # OK in sync route
    return {"status": "success"}
```

### 3. Dependency Injection Patterns

**Best Practice**: Use async generators for database sessions with proper cleanup.

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Engine setup (do once at startup)
async_engine = create_async_engine(
    "sqlite+aiosqlite:///./analytics.db",
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent "IO in unexpected place" errors
    autocommit=False,
    autoflush=False
)

# Dependency function
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 4. Chain Dependencies for Clean Code

```python
# ✅ GOOD: Chained dependencies
async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)

@router.post("/event")
async def track_event(
    event: EventRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    await analytics.log_event(event)
    return {"status": "success"}
```

### 5. Pydantic Models for Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class EventRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    session_id: str = Field(..., min_length=36, max_length=36)  # UUID
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['query', 'response', 'error', 'upload', 'tool_call', 'feedback']
        if v not in allowed_types:
            raise ValueError(f'Invalid event type. Must be one of {allowed_types}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "query",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "data": {"query_text": "What is the average?"},
                "metadata": {"endpoint": "/api/v1/chat"}
            }
        }
```

### 6. Error Handling

```python
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
import traceback

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log to analytics
    await analytics_service.log_error(
        session_id=request.headers.get("X-Session-ID"),
        error_type=type(exc).__name__,
        error_message=str(exc),
        stack_trace=traceback.format_exc(),
        endpoint=str(request.url.path)
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
```

### 7. Router Configuration

```python
# Organize routers with prefixes and tags
router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

# Apply dependencies to entire router
router = APIRouter(
    prefix="/api/v1/analytics",
    dependencies=[Depends(verify_session)]  # All routes require this
)
```

---

## SQLAlchemy Async Best Practices

### 1. Model Definition

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    data = Column(JSON, default={})
    metadata = Column(JSON, default={})

    # Composite index for common queries
    __table_args__ = (
        Index('idx_session_event_time', 'session_id', 'event_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, type={self.event_type}, session={self.session_id})>"
```

### 2. Session Management

**Rule**: One AsyncSession per async task. Never share across concurrent tasks.

```python
# ✅ GOOD: Separate session per task
async def process_events():
    tasks = []
    for event in events:
        task = process_single_event(event)
        tasks.append(task)
    await asyncio.gather(*tasks)

async def process_single_event(event):
    async with AsyncSessionLocal() as session:  # New session per task
        # Process event
        await session.commit()

# ❌ BAD: Shared session across tasks
async def process_events_bad():
    async with AsyncSessionLocal() as session:
        tasks = []
        for event in events:
            task = process_single_event(session, event)  # DANGEROUS!
            tasks.append(task)
        await asyncio.gather(*tasks)
```

### 3. CRUD Operations

```python
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(self, event_data: dict) -> AnalyticsEvent:
        """Create new event"""
        event = AnalyticsEvent(**event_data)
        self.db.add(event)
        await self.db.flush()  # Get ID without committing
        await self.db.refresh(event)  # Load relationships if any
        return event

    async def get_events_by_session(self, session_id: str) -> list[AnalyticsEvent]:
        """Query events"""
        stmt = select(AnalyticsEvent).where(
            AnalyticsEvent.session_id == session_id
        ).order_by(AnalyticsEvent.timestamp.desc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_session(self, session_id: str, updates: dict):
        """Update records"""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(**updates)
        )
        await self.db.execute(stmt)

    async def delete_old_events(self, days: int):
        """Bulk delete"""
        cutoff_date = datetime.now() - timedelta(days=days)
        stmt = delete(AnalyticsEvent).where(
            AnalyticsEvent.timestamp < cutoff_date
        )
        result = await self.db.execute(stmt)
        return result.rowcount
```

### 4. Relationships and Eager Loading

```python
from sqlalchemy.orm import relationship, selectinload

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    # ... other columns ...

    # Define relationship
    feedback = relationship("QueryFeedback", back_populates="session")

class QueryFeedback(Base):
    __tablename__ = "query_feedback"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"))

    # Define relationship
    session = relationship("Session", back_populates="feedback")

# Eager load to avoid N+1 queries
async def get_session_with_feedback(session_id: str):
    stmt = (
        select(Session)
        .options(selectinload(Session.feedback))  # Eager load
        .where(Session.id == session_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

### 5. Transactions and Error Handling

```python
async def complex_operation(db: AsyncSession):
    try:
        # Multiple operations in transaction
        event = AnalyticsEvent(...)
        db.add(event)

        await db.flush()  # Get ID but don't commit yet

        feedback = QueryFeedback(query_event_id=event.id, ...)
        db.add(feedback)

        await db.commit()  # Commit all together
    except Exception as e:
        await db.rollback()  # Rollback on error
        raise
```

---

## React Best Practices

### 1. Custom Hooks - Single Responsibility

```javascript
// ✅ GOOD: Single purpose hooks
const useSessionId = () => {
  const [sessionId, setSessionId] = useState(() => {
    const existing = localStorage.getItem('analytics_session_id');
    if (existing) return existing;

    const newId = uuidv4();
    localStorage.setItem('analytics_session_id', newId);
    return newId;
  });

  return sessionId;
};

const useAnalyticsTracking = (sessionId) => {
  const trackEvent = useCallback(async (eventType, data, metadata = {}) => {
    try {
      await axios.post('/api/v1/analytics/event', {
        event_type: eventType,
        session_id: sessionId,
        data,
        metadata
      }, {
        headers: { 'X-Session-ID': sessionId }
      });
    } catch (error) {
      console.error('Analytics tracking failed:', error);
    }
  }, [sessionId]);

  return { trackEvent };
};

// Compose hooks
const useAnalytics = () => {
  const sessionId = useSessionId();
  const { trackEvent } = useAnalyticsTracking(sessionId);

  return { sessionId, trackEvent };
};
```

### 2. Context Best Practices

**Rule**: Call `useContext` inside custom hooks (explicit is better than implicit).

```javascript
// ✅ GOOD: useContext inside custom hook
import { createContext, useContext } from 'react';

const SessionContext = createContext(null);

export const SessionProvider = ({ children }) => {
  const sessionId = useSessionId();

  // Memoize context value to prevent unnecessary re-renders
  const value = useMemo(() => ({ sessionId }), [sessionId]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};

// Custom hook with error handling
export const useSession = () => {
  const context = useContext(SessionContext);

  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }

  return context;
};

// Usage
const MyComponent = () => {
  const { sessionId } = useSession();
  return <div>{sessionId}</div>;
};
```

### 3. Performance Optimization

```javascript
// ✅ GOOD: Memoization for expensive operations
const FeedbackButtons = ({ messageId, queryEventId }) => {
  const [rating, setRating] = useState(null);
  const { sessionId } = useSession();

  // Memoize callback to prevent re-creation
  const handleFeedback = useCallback(async (value) => {
    setRating(value);

    try {
      await fetch('/api/v1/analytics/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          message_id: messageId,
          query_event_id: queryEventId,
          rating: value
        })
      });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  }, [messageId, queryEventId, sessionId]);

  return (
    <div>
      <button onClick={() => handleFeedback(1)}>
        <ThumbsUp />
      </button>
      <button onClick={() => handleFeedback(-1)}>
        <ThumbsDown />
      </button>
    </div>
  );
};

// Memoize component to prevent unnecessary re-renders
export default React.memo(FeedbackButtons);
```

### 4. Hook Rules

```javascript
// ✅ GOOD: Hooks at top level
const MyComponent = () => {
  const { sessionId } = useSession();  // Top level
  const { trackEvent } = useAnalytics();  // Top level

  const handleClick = () => {
    trackEvent('button_click', { button: 'submit' });
  };

  return <button onClick={handleClick}>Submit</button>;
};

// ❌ BAD: Hooks in conditionals or loops
const MyComponent = ({ condition }) => {
  if (condition) {
    const { sessionId } = useSession();  // WRONG!
  }

  for (let i = 0; i < 10; i++) {
    const value = useState(i);  // WRONG!
  }
};
```

### 5. useEffect Cleanup

```javascript
// ✅ GOOD: Proper cleanup
const SessionTracker = () => {
  const { sessionId } = useSession();

  useEffect(() => {
    // Track session start
    const startTime = Date.now();

    const trackSessionStart = async () => {
      await fetch('/api/v1/analytics/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'session_start',
          session_id: sessionId
        })
      });
    };

    trackSessionStart();

    // Cleanup function
    return () => {
      const duration = Date.now() - startTime;

      // Track session end
      fetch('/api/v1/analytics/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'session_end',
          session_id: sessionId,
          data: { duration_ms: duration }
        })
      });
    };
  }, [sessionId]);

  return null;
};
```

### 6. Error Boundaries

```javascript
import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log to analytics
    fetch('/api/v1/analytics/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: 'error',
        data: {
          error: error.toString(),
          errorInfo: errorInfo.componentStack
        }
      })
    });
  }

  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong.</h1>;
    }

    return this.props.children;
  }
}

// Usage
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

---

## General Best Practices

### 1. Type Safety

```python
# Python: Use type hints
from typing import Optional, Dict, Any, List

async def log_event(
    event_type: str,
    session_id: str,
    data: Optional[Dict[str, Any]] = None
) -> AnalyticsEvent:
    ...
```

```javascript
// JavaScript: Use JSDoc for documentation
/**
 * Track an analytics event
 * @param {string} eventType - Type of event
 * @param {Object} data - Event data
 * @param {Object} metadata - Event metadata
 * @returns {Promise<void>}
 */
const trackEvent = async (eventType, data, metadata) => {
  ...
};
```

### 2. Environment Variables

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./analytics.db"
    analytics_enabled: bool = True
    analytics_batch_size: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Testing

```python
# Test with pytest-asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_log_event(db_session):
    service = AnalyticsService(db_session)
    event = await service.log_event("test", "session-123", {"foo": "bar"})
    assert event.event_type == "test"
```

### 4. Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use structured logging
logger.info(
    "Event logged",
    extra={
        "event_type": "query",
        "session_id": session_id,
        "duration_ms": duration
    }
)
```

---

## Summary Checklist

### FastAPI ✅
- [ ] Use async/await correctly (non-blocking I/O only)
- [ ] Implement dependency injection for database sessions
- [ ] Use Pydantic models for validation
- [ ] Add proper error handling
- [ ] Structure by domain, not layers

### SQLAlchemy ✅
- [ ] Use AsyncSession with expire_on_commit=False
- [ ] One session per async task (no sharing)
- [ ] Use context managers (async with)
- [ ] Add indexes for common queries
- [ ] Handle transactions properly (commit/rollback)

### React ✅
- [ ] Single-purpose custom hooks
- [ ] Call useContext inside hooks with error handling
- [ ] Memoize context values and callbacks
- [ ] Follow hook rules (top level only)
- [ ] Add useEffect cleanup
- [ ] Use React.memo for expensive components

### General ✅
- [ ] Use type hints/JSDoc
- [ ] Environment variables for configuration
- [ ] Write tests
- [ ] Add structured logging
- [ ] Document complex logic

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Status**: Reference for Implementation
