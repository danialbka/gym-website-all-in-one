-- Add weight column to users table
-- This migration adds a weight field to store user's body weight

ALTER TABLE users ADD COLUMN weight FLOAT;

-- Optional: Add a comment to the column
COMMENT ON COLUMN users.weight IS 'User body weight in kilograms';