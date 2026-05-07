# 🔧 COMPLETE TROUBLESHOOTING GUIDE

## ✅ Current Project Status

**All Services Running Successfully:**
- ✅ Backend: HEALTHY (http://localhost:8000)
- ✅ Frontend: RUNNING (http://localhost:3000)
- ✅ PostgreSQL: CONNECTED
- ✅ Redis: CONNECTED
- ✅ API Keys: CONFIGURED

---

## 🎯 Quick Verification

Run this command to verify everything:
```cmd
verify_project.bat
```

Or manually check:
```cmd
# Check containers
docker-compose ps

# Test backend
curl http://localhost:8000/api/v1/health/

# Test frontend
curl http://localhost:3000/health
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Backend Shows "Unhealthy"

**Symptoms:**
- `docker-compose ps` shows backend as "unhealthy"
- Backend logs show import errors

**Solution:**
```cmd
# Stop everything
docker-compose down

# Rebuild with no cache
docker-compose build --no-cache backend

# Start again
docker-compose up -d
```

**Check logs:**
```cmd
docker-compose logs backend --tail=50
```

---

### Issue 2: "RegisterRequest not defined" Error

**Cause:** Import issues in auth.py

**Solution:**
File: `backend/app/api/v1/auth.py`

Ensure imports look like this (NO `from __future__ import annotations`):
```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from app.core.dependencies import get_current_user, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import AuthService
```

After fixing, rebuild:
```cmd
docker-compose up --build -d backend
```

---

### Issue 3: Database Connection Failed

**Symptoms:**
- Backend logs show "password authentication failed"
- Migrator container exits with error

**Solution:**
```cmd
# Clean all volumes (WARNING: Deletes all data)
docker-compose down -v

# Start fresh
docker-compose up -d
```

**Verify .env files match:**
- Main `.env`: `POSTGRES_PASSWORD=docqa_secure_password_2024`
- Backend `.env`: `DATABASE_URL=postgresql+asyncpg://docqa:docqa_secure_password_2024@postgres:5432/docqa_db`

---

### Issue 4: Frontend Not Loading

**Symptoms:**
- Browser shows "Cannot connect" or blank page
- Frontend container is unhealthy

**Solution:**
```cmd
# Check frontend logs
docker-compose logs frontend --tail=30

# Rebuild frontend
docker-compose up --build -d frontend

# Test health endpoint
curl http://localhost:3000/health
```

---

### Issue 5: API Keys Not Working

**Symptoms:**
- Chat returns errors
- Document processing fails
- "API key invalid" errors

**Solution:**

1. **Check backend/.env file:**
```bash
# Google Gemini (Required for chat)
GOOGLE_API_KEY=AIzaSy...  # Must start with AIzaSy

# Pinecone (Required for vector search)
PINECONE_API_KEY=pcsk_...  # Must start with pcsk_

# OpenAI (Optional)
OPENAI_API_KEY=sk-proj-...  # Must start with sk-
```

2. **Restart backend after changing keys:**
```cmd
docker-compose restart backend
```

3. **Verify keys are loaded:**
```cmd
docker-compose exec backend env | findstr API_KEY
```

---

### Issue 6: Port Already in Use

**Symptoms:**
- "port is already allocated" error
- Cannot start containers

**Solution:**
```cmd
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml
# Change "8000:8000" to "8001:8000"
```

---

### Issue 7: Out of Disk Space

**Symptoms:**
- Build fails with "no space left"
- Containers crash randomly

**Solution:**
```cmd
# Clean unused Docker resources
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Check disk usage
docker system df
```

---

## 🔄 Complete Fresh Start

If nothing works, do a complete reset:

```cmd
# 1. Stop and remove everything
docker-compose down -v

# 2. Remove all Docker resources
docker system prune -a --volumes

# 3. Rebuild from scratch
docker-compose build --no-cache

# 4. Start services
docker-compose up -d

# 5. Wait 30 seconds, then check
timeout /t 30 /nobreak
docker-compose ps
```

---

## 📊 Health Check Commands

### Backend Health:
```cmd
curl http://localhost:8000/api/v1/health/
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-05-07T..."
}
```

### Frontend Health:
```cmd
curl http://localhost:3000/health
```

Expected response:
```
ok
```

### Database Connection:
```cmd
docker-compose exec postgres psql -U docqa -d docqa_db -c "\dt"
```

Should show list of tables.

### Redis Connection:
```cmd
docker-compose exec redis redis-cli ping
```

Should return: `PONG`

---

## 🔍 Debugging Commands

### View all logs:
```cmd
docker-compose logs -f
```

### View specific service logs:
```cmd
docker-compose logs backend -f
docker-compose logs frontend -f
docker-compose logs postgres -f
```

### Enter container shell:
```cmd
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Check environment variables:
```cmd
docker-compose exec backend env
```

### Check running processes:
```cmd
docker-compose exec backend ps aux
```

---

## 📝 Configuration Files Checklist

### ✅ Main .env (Project Root)
```
POSTGRES_USER=docqa
POSTGRES_PASSWORD=docqa_secure_password_2024
POSTGRES_DB=docqa_db
SECRET_KEY=<64-char-hex-string>
```

### ✅ backend/.env
```
DATABASE_URL=postgresql+asyncpg://docqa:docqa_secure_password_2024@postgres:5432/docqa_db
REDIS_URL=redis://redis:6379/0
GOOGLE_API_KEY=<your-key>
PINECONE_API_KEY=<your-key>
```

### ✅ docker-compose.yml
- All services defined
- Health checks configured
- Volumes mounted
- Networks configured

---

## 🚀 Performance Optimization

### If backend is slow:
```cmd
# Increase worker processes
# Edit docker-compose.yml, add to backend environment:
WORKERS=4
```

### If database is slow:
```cmd
# Increase shared buffers
# Add to postgres environment:
POSTGRES_SHARED_BUFFERS=256MB
```

### If Redis is slow:
```cmd
# Enable persistence
# Already configured with AOF
```

---

## 📞 Getting Help

### Check logs first:
```cmd
docker-compose logs --tail=100 > logs.txt
```

### Check container status:
```cmd
docker-compose ps > status.txt
```

### Check system resources:
```cmd
docker stats --no-stream > resources.txt
```

Send these files when asking for help.

---

## ✅ Success Indicators

Your project is working correctly if:

1. ✅ `docker-compose ps` shows all services as "healthy" or "running"
2. ✅ `curl http://localhost:8000/api/v1/health/` returns `{"status":"healthy"}`
3. ✅ `curl http://localhost:3000/health` returns `ok`
4. ✅ Browser can open http://localhost:3000
5. ✅ You can register and login
6. ✅ You can upload files
7. ✅ You can ask questions and get responses

---

**Last Updated:** May 7, 2026
**Status:** All systems operational ✅
