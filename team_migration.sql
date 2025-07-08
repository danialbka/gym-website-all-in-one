-- Team Feature Migration Script
-- Adds team/gym functionality to the GymRank database

-- Add team field to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS team VARCHAR(100);

-- Create index for team field for performance
CREATE INDEX IF NOT EXISTS idx_users_team ON users(team);

-- Update existing users with sample teams (optional - for testing)
-- Users can update their teams through the registration/profile update process
UPDATE users 
SET team = CASE 
    WHEN username = 'Danial' THEN 'Iron Temple Gym'
    WHEN username = 'TestUser' THEN 'PowerHouse Fitness'
    ELSE 'Independent'
END
WHERE team IS NULL;

-- Show updated table structure
\d users;