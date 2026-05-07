#!/bin/bash
# =============================================================================
# Infrastructure Health Check Script
# =============================================================================
# Usage: bash health_check.sh
# Purpose: Verify all services are running and functional

set -e

echo "🔍 Starting Infrastructure Health Check..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# 1. Check Docker Services
# -----------------------------------------------------------------------------
echo "📦 Checking Docker Services..."

if ! docker compose ps | grep -q "Up"; then
    echo -e "${RED}❌ Docker services not running${NC}"
    echo "Run: docker compose up -d"
    exit 1
fi

# Check individual services
services=("postgres" "redis" "backend" "frontend")
for service in "${services[@]}"; do
    if docker compose ps | grep "$service" | grep -q "Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
    else
        echo -e "${RED}❌ $service is not running${NC}"
        exit 1
    fi
done

echo ""

# -----------------------------------------------------------------------------
# 2. Check PostgreSQL Connection
# -----------------------------------------------------------------------------
echo "🗄️  Checking PostgreSQL..."

if docker compose exec -T postgres pg_isready -U docqa > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL connection failed${NC}"
    exit 1
fi

# Check if tables exist
table_count=$(docker compose exec -T postgres psql -U docqa -d docqa_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

if [ "$table_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Database tables exist ($table_count tables)${NC}"
else
    echo -e "${YELLOW}⚠️  No tables found - migrations may be needed${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# 3. Check Redis Connection
# -----------------------------------------------------------------------------
echo "💾 Checking Redis..."

if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✅ Redis is responding${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# 4. Check Backend Health Endpoints
# -----------------------------------------------------------------------------
echo "🔌 Checking Backend API..."

# Wait for backend to be ready
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/api/v1/health/ > /dev/null 2>&1; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Backend health check timeout${NC}"
    exit 1
fi

# Basic health check
health_response=$(curl -s http://localhost:8000/api/v1/health/)
if echo "$health_response" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend basic health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    exit 1
fi

# Readiness check (DB + Redis)
ready_response=$(curl -s http://localhost:8000/api/v1/health/ready)
if echo "$ready_response" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend readiness check passed (DB + Redis connected)${NC}"
else
    echo -e "${YELLOW}⚠️  Backend readiness check failed - check DB/Redis connection${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# 5. Check Frontend
# -----------------------------------------------------------------------------
echo "🌐 Checking Frontend..."

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend connection failed${NC}"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# 6. Check Environment Variables
# -----------------------------------------------------------------------------
echo "🔑 Checking Critical Environment Variables..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check for placeholder values
if grep -q "YOUR_OPENAI_API_KEY_HERE" .env; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not configured (using placeholder)${NC}"
    echo "   Set your OpenAI API key in .env file"
fi

if grep -q "YOUR_PINECONE_API_KEY_HERE" .env; then
    echo -e "${YELLOW}⚠️  PINECONE_API_KEY not configured (using placeholder)${NC}"
    echo "   Set your Pinecone API key in .env file"
fi

echo ""

# -----------------------------------------------------------------------------
# 7. Check Ports
# -----------------------------------------------------------------------------
echo "🔌 Checking Port Availability..."

ports=("3000:Frontend" "8000:Backend" "5432:PostgreSQL" "6379:Redis")
for port_info in "${ports[@]}"; do
    port="${port_info%%:*}"
    service="${port_info##*:}"
    
    if netstat -an 2>/dev/null | grep -q ":$port.*LISTEN" || ss -tuln 2>/dev/null | grep -q ":$port"; then
        echo -e "${GREEN}✅ Port $port ($service) is in use${NC}"
    else
        echo -e "${YELLOW}⚠️  Port $port ($service) not listening${NC}"
    fi
done

echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Infrastructure Health Check Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Service URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs (if DEBUG=true)"
echo ""
echo "🔧 Next Steps:"
echo "   1. Configure API keys in .env file"
echo "   2. Run feature tests: bash test_features.sh"
echo "   3. Open browser: http://localhost:3000"
echo ""
