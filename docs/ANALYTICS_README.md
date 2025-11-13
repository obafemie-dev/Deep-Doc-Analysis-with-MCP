# Analytics System - Quick Start Guide

## Overview

The Deep Doc Analysis application now includes a comprehensive analytics system to track user interactions, AI responses, errors, and feedback. This guide will help you get started with the analytics features.

## What Gets Tracked

### Automatic Tracking (via Middleware)
- ✅ All API requests (endpoint, method, duration, status code)
- ✅ Request performance metrics
- ✅ Session IDs from headers

### User Interactions (Frontend)
- ✅ User queries and questions
- ✅ Chat clearing events
- ✅ Session start/end
- ✅ User feedback (thumbs up/down) on AI responses

### AI Performance
- ✅ Response generation time
- ✅ Tool usage (which MCP tools were called)
- ✅ Response success/failure
- ✅ Error logging with stack traces

## Setup

### 1. Install Dependencies

Backend dependencies are already added to `requirements.txt`:
- `sqlalchemy==2.0.36`
- `aiosqlite==0.20.0`

Install them:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Analytics (Optional)

Analytics is enabled by default. To configure, edit `backend/app/config.py` or set environment variables:

```env
# .env file
ANALYTICS_ENABLED=True
ANALYTICS_DB_URL=sqlite+aiosqlite:///./analytics.db
ANALYTICS_RETENTION_DAYS=90
```

### 3. Start the Application

The analytics database will be automatically created on first startup:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

You should see in the logs:
```
INFO:     Analytics middleware enabled
INFO:     Analytics database initialized successfully
```

### 4. Verify Analytics is Working

Check the analytics health endpoint:
```bash
curl http://localhost:8000/api/v1/analytics/health
```

Expected response:
```json
{
  "status": "healthy",
  "analytics_enabled": true,
  "database_url": "sqlite+aiosqlite:///"
}
```

## Database Location

The analytics database is stored at:
```
backend/analytics.db
```

## Viewing Analytics Data

### Option 1: Direct SQL Queries

```bash
cd backend
sqlite3 analytics.db
```

Example queries:
```sql
-- Total sessions
SELECT COUNT(*) FROM sessions;

-- Total queries today
SELECT COUNT(*) FROM analytics_events
WHERE event_type = 'query'
AND DATE(timestamp) = DATE('now');

-- Feedback satisfaction rate
SELECT
  SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as satisfaction_rate
FROM query_feedback;

-- Most common errors
SELECT error_type, COUNT(*) as count
FROM error_logs
GROUP BY error_type
ORDER BY count DESC
LIMIT 10;
```

### Option 2: Analytics API Endpoint

Get a summary of analytics for the last 7 days:
```bash
curl http://localhost:8000/api/v1/analytics/summary?days=7
```

Response:
```json
{
  "total_sessions": 150,
  "total_queries": 1250,
  "total_responses": 1200,
  "total_errors": 50,
  "average_response_time_ms": 2345.67,
  "positive_feedback_rate": 0.85,
  "total_feedback": 200,
  "time_period": "last_7_days"
}
```

### Option 3: Metabase Dashboard (Recommended)

For visual analytics, use Metabase (open-source BI tool):

#### Quick Setup:
```bash
docker run -d \
  --name metabase \
  -p 3000:3000 \
  -v metabase-data:/metabase-data \
  metabase/metabase
```

#### Connect to Database:
1. Open http://localhost:3000
2. Complete initial setup
3. Add database:
   - **Database type**: SQLite
   - **Database file**: `/path/to/backend/analytics.db`
4. Start building dashboards!

#### Recommended Dashboards:
1. **Usage Dashboard**: Sessions, queries, and file uploads over time
2. **Performance Dashboard**: Response times, tool execution times
3. **Quality Dashboard**: Feedback ratings, error rates
4. **Tools Dashboard**: Which MCP tools are most used

## Database Schema

### Tables

#### `analytics_events`
Unified event log for all types of events.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| event_type | TEXT | Type: query, response, error, upload, etc. |
| session_id | TEXT | UUID session identifier |
| timestamp | DATETIME | When event occurred |
| data | JSON | Event-specific data |
| metadata | JSON | Performance metrics, context |

#### `sessions`
Track user sessions and engagement.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Session UUID (primary key) |
| started_at | DATETIME | Session start time |
| ended_at | DATETIME | Session end time (nullable) |
| last_activity_at | DATETIME | Last activity timestamp |
| message_count | INTEGER | Number of messages |
| file_count | INTEGER | Number of files uploaded |
| llm_provider | TEXT | ollama or claude |
| total_query_time_ms | INTEGER | Total query processing time |

#### `query_feedback`
User feedback on AI responses.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Foreign key to sessions |
| message_id | TEXT | Frontend message ID |
| query_event_id | INTEGER | Foreign key to analytics_events |
| rating | INTEGER | 1 (thumbs up) or -1 (thumbs down) |
| comment | TEXT | Optional user comment |
| timestamp | DATETIME | Feedback timestamp |

#### `error_logs`
Detailed error tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Session UUID (nullable) |
| error_type | TEXT | Exception class name |
| error_message | TEXT | Error message |
| stack_trace | TEXT | Full stack trace |
| endpoint | TEXT | API endpoint where error occurred |
| request_data | JSON | Request context |
| timestamp | DATETIME | Error timestamp |

## Frontend Integration

### Session Management

Sessions are automatically managed with UUIDs stored in localStorage:

```javascript
import { useSession } from './contexts/SessionContext';

function MyComponent() {
  const { sessionId } = useSession();
  // sessionId is automatically included in all analytics requests
}
```

### Tracking Events

```javascript
import { useAnalytics } from './hooks/useAnalytics';

function MyComponent() {
  const { trackEvent, submitFeedback, trackQuery } = useAnalytics();

  // Track custom event
  await trackEvent('custom_action', { action: 'button_click' });

  // Track query
  await trackQuery('What is the average sales?', '/uploads/file.xlsx', 1);

  // Submit feedback
  await submitFeedback('msg_123', 1); // 1 = thumbs up, -1 = thumbs down
}
```

### Feedback Buttons

Feedback buttons are automatically displayed on all assistant messages:

```jsx
import FeedbackButtons from './components/FeedbackButtons';

<FeedbackButtons
  messageId="msg_123"
  queryEventId={null}
/>
```

## API Endpoints

### Track Event
```bash
POST /api/v1/analytics/event
Content-Type: application/json
X-Session-ID: <session-uuid>

{
  "event_type": "query",
  "session_id": "<session-uuid>",
  "data": {
    "query_text": "What is the average sales?",
    "file_path": "/uploads/sales.xlsx"
  },
  "metadata": {
    "duration_ms": 1234
  }
}
```

### Submit Feedback
```bash
POST /api/v1/analytics/feedback
Content-Type: application/json
X-Session-ID: <session-uuid>

{
  "message_id": "msg_123",
  "session_id": "<session-uuid>",
  "rating": 1,
  "comment": "Great analysis!"
}
```

### Get Summary
```bash
GET /api/v1/analytics/summary?days=7
```

### Start Session
```bash
POST /api/v1/analytics/session/start
Content-Type: application/json

{
  "session_id": "<session-uuid>",
  "llm_provider": "claude"
}
```

### End Session
```bash
POST /api/v1/analytics/session/end?session_id=<session-uuid>
```

## Data Retention

By default, analytics data is retained for 90 days. To cleanup old data:

```python
from app.services.analytics_service import AnalyticsService
from app.database import AsyncSessionLocal

async def cleanup():
    async with AsyncSessionLocal() as db:
        analytics = AnalyticsService(db)
        deleted_count = await analytics.cleanup_old_events(days=90)
        print(f"Deleted {deleted_count} old events")
```

## Privacy Considerations

### Current Implementation (Phase 1)
- **Session-based tracking** (no user identification)
- **UUID sessions** stored in browser localStorage
- **No PII collected** (no names, emails, IP addresses)
- **Data stored locally** in your own database

### Future (Phase 2 - User Authentication)
When adding user authentication:
- Add `user_id` column to sessions table
- Link sessions to authenticated users
- Implement data deletion requests (GDPR)
- Add opt-out mechanism

## Troubleshooting

### Analytics not working

1. Check if analytics is enabled:
```python
from app.config import settings
print(settings.ANALYTICS_ENABLED)  # Should be True
```

2. Check database exists:
```bash
ls -la backend/analytics.db
```

3. Check logs for errors:
```bash
# Look for analytics-related errors in server logs
```

### Database locked errors

SQLite can have concurrency issues. If you see "database locked" errors:
- Ensure only one process is writing at a time
- Consider migrating to PostgreSQL for production

### Feedback buttons not showing

1. Verify SessionProvider wraps your app in `App.jsx`
2. Check browser console for errors
3. Ensure `FeedbackButtons` component is imported in `MessageList.jsx`

## Migration to PostgreSQL

For production or high-traffic deployments, migrate to PostgreSQL:

1. Install PostgreSQL and dependencies:
```bash
pip install asyncpg
```

2. Update config:
```python
ANALYTICS_DB_URL = "postgresql+asyncpg://user:password@localhost/analytics"
```

3. Migrate data using pgloader:
```bash
pgloader sqlite:///./analytics.db postgresql://user:password@localhost/analytics
```

## Next Steps

- ✅ Set up Metabase for visual dashboards
- ✅ Create custom analytics queries for your use case
- ✅ Monitor feedback rates to improve AI responses
- ✅ Track which tools are most useful to users
- ✅ Identify and fix common errors

## Support

For more information, see:
- [Analytics Implementation Plan](./ANALYTICS_IMPLEMENTATION_PLAN.md)
- [Coding Best Practices](./CODING_BEST_PRACTICES.md)

---

**Last Updated**: 2025-11-13
**Version**: 1.0
