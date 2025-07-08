-- Quick fix to add team column
ALTER TABLE users ADD COLUMN team VARCHAR(100) DEFAULT 'Independent';
CREATE INDEX idx_users_team ON users(team);