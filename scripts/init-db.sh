#!/bin/bash
# ============================================
# PostgreSQL Initialization Script
# ============================================
# Configures database with security best practices

set -e

echo "🔧 Initializing PostgreSQL database..."

# Create extensions if needed
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- Set timezone
    SET timezone = 'America/Sao_Paulo';
    
    -- Performance tuning
    ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
    
    -- Security: Revoke public schema privileges
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;
    GRANT CREATE ON SCHEMA public TO $POSTGRES_USER;
    
    -- Log configuration
    ALTER SYSTEM SET log_min_duration_statement = 1000;
    ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
    
    SELECT 'Database initialized successfully!' as status;
EOSQL

echo "✅ PostgreSQL initialization complete!"
