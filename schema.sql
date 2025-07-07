-- GymRank Database Schema for Neon PostgreSQL

-- Users table
CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY,
    flag VARCHAR(10) NOT NULL,
    elo FLOAT DEFAULT 1000.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PRs (Personal Records) table
CREATE TABLE prs (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    lift_type VARCHAR(20) NOT NULL, -- bench, deadlift, squat
    weight FLOAT NOT NULL,
    video_url TEXT, -- optional for future video uploads
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_users_elo ON users(elo DESC);
CREATE INDEX idx_prs_username ON prs(username);
CREATE INDEX idx_prs_lift_type ON prs(lift_type);

-- Insert some sample data (optional)
INSERT INTO users (username, flag, elo) VALUES 
('Danial', '🇲🇾', 1200.0),
('TestUser', '🇺🇸', 1100.0);

INSERT INTO prs (username, lift_type, weight) VALUES 
('Danial', 'bench', 100.0),
('Danial', 'deadlift', 150.0),
('Danial', 'squat', 120.0),
('TestUser', 'bench', 80.0),
('TestUser', 'deadlift', 140.0);