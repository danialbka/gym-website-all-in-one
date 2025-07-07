-- Migration script to update existing GymRank database for login feature
-- Run this ONLY if you have an existing database that needs to be updated

-- Add new columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS email VARCHAR(100),
ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- Create unique constraint on email (if it doesn't exist)
DO $$ 
BEGIN
    BEGIN
        ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
    EXCEPTION
        WHEN duplicate_table THEN 
            -- Constraint already exists, do nothing
            NULL;
    END;
END $$;

-- Create new indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Update existing users with temporary data
-- WARNING: This sets a default password for existing users!
-- Users will need to register again or you'll need to implement password reset
UPDATE users 
SET 
    password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/3.o3nT3RgUe6P1bWe', -- Default: 'password123'
    display_name = username,
    is_active = TRUE
WHERE password_hash IS NULL;

-- Make password_hash NOT NULL after setting defaults
ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;

-- Show updated table structure
\d users;