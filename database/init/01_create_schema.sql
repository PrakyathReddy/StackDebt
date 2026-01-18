-- StackDebt Encyclopedia Database Schema
-- Creates the foundation for storing software version release dates

-- Create component category enum
CREATE TYPE component_category AS ENUM (
    'operating_system',
    'programming_language', 
    'database',
    'web_server',
    'framework',
    'library',
    'development_tool'
);

-- Create version releases table
CREATE TABLE version_releases (
    id SERIAL PRIMARY KEY,
    software_name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    release_date DATE NOT NULL,
    end_of_life_date DATE,
    category component_category NOT NULL,
    is_lts BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(software_name, version)
);

-- Create indexes for performance optimization
CREATE INDEX idx_software_version ON version_releases(software_name, version);
CREATE INDEX idx_release_date ON version_releases(release_date);
CREATE INDEX idx_category ON version_releases(category);
CREATE INDEX idx_software_name ON version_releases(software_name);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_version_releases_updated_at 
    BEFORE UPDATE ON version_releases 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();