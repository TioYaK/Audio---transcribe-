# ============================================================================
# QUICK DEPLOYMENT GUIDE - Security Hardened Version
# ============================================================================

# STEP 1: Secrets already generated ✅
# Location: ./secrets/ (7 files)
# Admin Password: 7OIeiHAcrPlXOQpssBWuSlm0
# Grafana Password: Sm7LkHlzEfFJ6dZrKwGHyySP

# STEP 2: Update .env file
# Remove these lines (now using secrets):
# DB_PASSWORD=...
# REDIS_PASSWORD=...
# SECRET_KEY=...
# ADMIN_PASSWORD=...

# Add these lines:
DB_USER=careca
DB_NAME=carecadb
DB_HOST=db
DB_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
HOST_USER_ID=1000
HOST_GROUP_ID=1000

# STEP 3: Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# STEP 4: Verify deployment
docker-compose ps
docker-compose logs -f app
docker-compose logs -f worker

# STEP 5: Test health endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl -I http://localhost:8000/

# OPTIONAL: Enable GPU support
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# OPTIONAL: Enable monitoring
docker-compose --profile monitoring up -d
# Prometheus: http://localhost:9090 (user: prometheus)
# Grafana: http://localhost:3000 (user: admin)

# ============================================================================
# VERIFICATION COMMANDS
# ============================================================================

# Check no passwords in environment
docker inspect careca-app | grep -i password
# Should return nothing

# Check security headers
curl -I http://localhost:8000/ | grep -E "X-Frame|X-Content|CSP"

# Check rate limiting
for i in {1..35}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/; done
# Should see 429 (Too Many Requests) after 30 requests

# Check secrets files
ls -la secrets/
# Should show 7 .txt files

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If app fails to start:
docker-compose logs app | tail -50

# If worker fails:
docker-compose logs worker | tail -50

# If database connection fails:
docker-compose exec db pg_isready -U careca

# If Redis fails:
docker-compose exec redis redis-cli -a $(cat secrets/redis_password.txt) ping

# Reset everything:
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# ============================================================================
