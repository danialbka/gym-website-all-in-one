-- GymRank Database Schema for Neon PostgreSQL

-- Users table
CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    display_name VARCHAR(100),
    flag VARCHAR(10) NOT NULL,
    elo FLOAT DEFAULT 1000.0,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
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
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_prs_username ON prs(username);
CREATE INDEX idx_prs_lift_type ON prs(lift_type);

-- Insert some sample data (optional)
-- Note: These are temporary demo passwords. In production, use proper hashing!
INSERT INTO users (username, password_hash, email, display_name, flag, elo) VALUES 
('Danial', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/3.o3nT3RgUe6P1bWe', 'danial@gymrank.com', 'Danial', '🇲🇾', 1200.0),
('TestUser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/3.o3nT3RgUe6P1bWe', 'test@gymrank.com', 'Test User', '🇺🇸', 1100.0);

INSERT INTO prs (username, lift_type, weight) VALUES 
('Danial', 'bench', 100.0),
('Danial', 'deadlift', 150.0),
('Danial', 'squat', 120.0),
('TestUser', 'bench', 80.0),
('TestUser', 'deadlift', 140.0);