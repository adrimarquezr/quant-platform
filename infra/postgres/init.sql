-- =============================================================================
-- PostgreSQL Initialization — Quant Platform Schema
-- =============================================================================
-- This script runs once when the PostgreSQL container is first created.
-- It creates the application user and database if they don't exist.
-- Table creation is handled by SQLAlchemy's Base.metadata.create_all()
-- =============================================================================

-- Create schemas for logical separation
CREATE SCHEMA IF NOT EXISTS quant;
CREATE SCHEMA IF NOT EXISTS market;

-- Grant access
GRANT ALL PRIVILEGES ON SCHEMA quant TO quant_user;
GRANT ALL PRIVILEGES ON SCHEMA market TO quant_user;
