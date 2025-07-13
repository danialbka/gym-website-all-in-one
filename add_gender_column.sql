-- Add gender column to users table
-- This migration adds a gender field required for DOTS score calculation

ALTER TABLE users ADD COLUMN gender VARCHAR(10);

-- Optional: Add a comment to the column
COMMENT ON COLUMN users.gender IS 'User gender (male/female) for DOTS score calculation';

-- Optional: Add a check constraint to ensure only valid values
ALTER TABLE users ADD CONSTRAINT check_gender CHECK (gender IN ('male', 'female'));