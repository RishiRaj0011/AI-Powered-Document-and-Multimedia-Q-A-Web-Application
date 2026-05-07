# 📋 ENVIRONMENT CONFIGURATION GUIDE

## 🎯 File Structure Overview

```
d:\SDE Intern Project\
│
├── .env.example              ✅ Template for docker-compose
│   └── Used by: docker-compose.yml
│   └── Contains: Database credentials only
│
├── backend/
│   ├── .env                  ✅ Main backend configuration (DO NOT COMMIT)
│   │   └── Used by: FastAPI application
│   │   └── Contains: All API keys, database, Redis, etc.
│   │
│   └── .env.example          ✅ Template for backend
│       └── Used by: Developers as reference
│       └── Contains: All variables with placeholders
│
└── frontend/
    ├── .env.development      ✅ Development configuration
    │   └── Used by: Vite dev server
    │   └── Contains: API URL for local backend
    │
    ├── .env.production       ✅ Production configuration
    │   └── Used by: Vite build process
    │   └── Contains: API URL for production backend
    │
    └── .env.example          ✅ Template for frontend
        └── Used by: Developers as reference
        └── Contains: Variable descriptions
```

---

## 🔑 Which File Does What?

### **1. Root `.env.example`** (Template Only)
**Purpose:** Template for docker-compose environment variables  
**Used By:** Developers setting up the project  
**Contains:** PostgreSQL credentials only  
**Commit to Git:** ✅ YES (it's a template)

**When to use:**
- First time setup
- Creating `.env` for docker-compose
- Reference for database configuration

---

### **2. `backend/.env`** (Main Configuration)
**Purpose:** Backend application configuration  
**Used By:** FastAPI application running in Docker  
**Contains:** 
- Application secrets (SECRET_KEY)
- Database connection (DATABASE_URL)
- Redis connection (REDIS_URL)
- API keys (Google, Pinecone, OpenAI)
- CORS settings
- File upload limits
- JWT token settings

**Commit to Git:** ❌ NO (contains secrets)

**When to update:**
- After generating new API keys
- When changing database password
- When modifying CORS origins
- When adjusting file size limits

---

### **3. `backend/.env.example`** (Template)
**Purpose:** Template showing all available backend variables  
**Used By:** Developers as reference  
**Contains:** All variables with placeholder values  
**Commit to Git:** ✅ YES (it's a template)

**When to update:**
- When adding new configuration variables
- When changing default values
- When adding new features requiring config

---

### **4. `frontend/.env.development`** (Dev Config)
**Purpose:** Frontend development configuration  
**Used By:** Vite dev server (npm run dev)  
**Contains:** `VITE_API_URL=http://localhost:8000`  
**Commit to Git:** ✅ YES (no secrets, just local URL)

**When to update:**
- When backend port changes
- When using different local backend URL

---

### **5. `frontend/.env.production`** (Prod Config)
**Purpose:** Frontend production build configuration  
**Used By:** Vite build process (npm run build)  
**Contains:** `VITE_API_URL=http://backend:8000`  
**Commit to Git:** ✅ YES (Docker service name)

**When to update:**
- When deploying to production with different backend URL
- When using external API gateway

---

### **6. `frontend/.env.example`** (Template)
**Purpose:** Template for frontend environment variables  
**Used By:** Developers as reference  
**Contains:** Variable descriptions  
**Commit to Git:** ✅ YES (it's a template)

---

## 🚀 Setup Instructions

### **For First Time Setup:**

#### Step 1: Root Level (Docker Compose)
```bash
# NOT NEEDED - docker-compose reads from backend/.env
# Root .env is optional and only for database credentials
```

#### Step 2: Backend Configuration
```bash
cd backend

# Copy template
cp .env.example .env

# Edit and fill in your keys
notepad .env

# Required values:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
# - GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)
# - PINECONE_API_KEY (from https://app.pinecone.io/)
# - DATABASE_URL (already set for Docker)
```

#### Step 3: Frontend Configuration
```bash
cd frontend

# Development is already configured
# .env.development has: VITE_API_URL=http://localhost:8000

# Production is already configured
# .env.production has: VITE_API_URL=http://backend:8000

# No changes needed unless using custom URLs
```

---

## 📊 Variable Priority

### **Backend loads variables in this order:**
1. Environment variables from Docker
2. `backend/.env` file
3. Default values in code

### **Frontend loads variables in this order:**
1. `.env.production` (for production build)
2. `.env.development` (for dev server)
3. `.env.local` (if exists, highest priority)

---

## 🔐 Security Best Practices

### **DO:**
✅ Keep `backend/.env` in `.gitignore`  
✅ Use strong SECRET_KEY (64 characters)  
✅ Rotate API keys every 90 days  
✅ Use different keys for dev/staging/prod  
✅ Store production keys in secret manager  

### **DON'T:**
❌ Commit `backend/.env` to Git  
❌ Share API keys in chat/email  
❌ Use same keys across environments  
❌ Hardcode secrets in code  
❌ Use weak SECRET_KEY  

---

## 🛠️ Common Scenarios

### **Scenario 1: New Developer Setup**
```bash
# 1. Clone repository
git clone <repo-url>
cd project

# 2. Copy backend template
cd backend
cp .env.example .env

# 3. Get API keys from team lead
# 4. Fill in backend/.env
# 5. Start application
docker-compose up -d
```

### **Scenario 2: API Key Rotation**
```bash
# 1. Generate new keys from provider dashboards
# 2. Update backend/.env
# 3. Restart backend
docker-compose restart backend
```

### **Scenario 3: Production Deployment**
```bash
# 1. Use secret management (AWS Secrets Manager, Vault)
# 2. Inject secrets as environment variables
# 3. Don't use .env files in production
# 4. Use CI/CD to manage secrets
```

### **Scenario 4: Local Development Without Docker**
```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://docqa:password@localhost:5432/docqa_db
REDIS_URL=redis://localhost:6379/0

# frontend/.env.development
VITE_API_URL=http://localhost:8000
```

---

## 📝 Environment Variables Reference

### **Backend Variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ Yes | - | JWT signing key (64 chars) |
| `DEBUG` | No | `false` | Enable debug mode |
| `DATABASE_URL` | ✅ Yes | - | PostgreSQL connection string |
| `REDIS_URL` | ✅ Yes | - | Redis connection string |
| `GOOGLE_API_KEY` | ✅ Yes | - | Google Gemini API key |
| `PINECONE_API_KEY` | ✅ Yes | - | Pinecone vector DB key |
| `OPENAI_API_KEY` | No | - | OpenAI API key (optional) |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` | CORS origins |
| `MAX_FILE_SIZE_MB` | No | `50` | Max upload size |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT expiry |

### **Frontend Variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | ✅ Yes | - | Backend API base URL |

---

## 🔍 Troubleshooting

### **Issue: Backend can't connect to database**
```bash
# Check DATABASE_URL in backend/.env
# For Docker: use 'postgres' as host
DATABASE_URL=postgresql+asyncpg://docqa:password@postgres:5432/docqa_db

# For local: use 'localhost' as host
DATABASE_URL=postgresql+asyncpg://docqa:password@localhost:5432/docqa_db
```

### **Issue: Frontend can't reach backend**
```bash
# Check VITE_API_URL in frontend/.env.development
# Should be: http://localhost:8000

# Verify backend is running:
curl http://localhost:8000/api/v1/health/
```

### **Issue: API keys not working**
```bash
# 1. Verify keys are correct in backend/.env
# 2. Check for extra spaces or quotes
# 3. Restart backend: docker-compose restart backend
# 4. Check logs: docker-compose logs backend
```

---

## ✅ Verification Checklist

Before running the application:

- [ ] `backend/.env` exists and has all required keys
- [ ] `SECRET_KEY` is 64 characters long
- [ ] `GOOGLE_API_KEY` starts with `AIzaSy`
- [ ] `PINECONE_API_KEY` starts with `pcsk_`
- [ ] `DATABASE_URL` uses `postgres` as host (for Docker)
- [ ] `REDIS_URL` uses `redis` as host (for Docker)
- [ ] `frontend/.env.development` has correct API URL
- [ ] All `.env` files are in `.gitignore`

---

## 📚 Additional Resources

- **Generate SECRET_KEY:** `python -c "import secrets; print(secrets.token_hex(32))"`
- **Google Gemini Keys:** https://aistudio.google.com/app/apikey
- **Pinecone Keys:** https://app.pinecone.io/
- **OpenAI Keys:** https://platform.openai.com/api-keys

---

**Last Updated:** May 7, 2026  
**Version:** 2.0 (Cleaned and Optimized)
