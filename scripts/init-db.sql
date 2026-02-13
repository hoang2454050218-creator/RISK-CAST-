-- RISKCAST Database Initialization
-- This script runs when PostgreSQL container first starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for JSON fields (PostgreSQL specific)
-- These will be created after tables are set up by SQLAlchemy

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE riskcast TO riskcast;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'RISKCAST database initialized at %', NOW();
END $$;
