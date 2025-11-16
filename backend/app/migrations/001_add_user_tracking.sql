-- Migration: Add user tracking to analytics tables
-- Version: 001
-- Date: 2025-11-16
-- Description: Adds user_id columns and indexes to enable user-specific analytics

-- Step 1: Add user_id to analytics_events table
ALTER TABLE analytics_events
ADD COLUMN user_id VARCHAR(255);

-- Step 2: Add user_id to sessions table
ALTER TABLE sessions
ADD COLUMN user_id VARCHAR(255);

-- Step 3: Add user_id to query_feedback table
ALTER TABLE query_feedback
ADD COLUMN user_id VARCHAR(255);

-- Step 4: Add user_id to error_logs table
ALTER TABLE error_logs
ADD COLUMN user_id VARCHAR(255);

-- Step 5: Create index for analytics_events user queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);

-- Step 6: Create composite index for user + event type queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_event ON analytics_events(user_id, event_type, timestamp);

-- Step 7: Create index for sessions user queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Step 8: Create composite index for user session analytics
CREATE INDEX IF NOT EXISTS idx_sessions_user_started ON sessions(user_id, started_at);

-- Step 9: Create index for feedback user queries
CREATE INDEX IF NOT EXISTS idx_query_feedback_user_id ON query_feedback(user_id);

-- Step 10: Create composite index for user feedback analytics
CREATE INDEX IF NOT EXISTS idx_query_feedback_user_rating ON query_feedback(user_id, rating, timestamp);

-- Step 11: Create index for error_logs user queries
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
