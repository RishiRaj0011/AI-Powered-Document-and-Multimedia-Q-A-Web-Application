# AI Document & Multimedia Q&A Platform

![CI](https://img.shields.io/github/actions/workflow/status/yourusername/docqa/ci.yml?branch=main&label=CI&logo=github)
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)
![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
![License](https://img.shields.io/badge/license-MIT-green)

A production-grade full-stack web application that enables users to upload documents (PDF, DOCX, TXT) and multimedia files (audio/video), then ask natural language questions answered by GPT-4o using RAG (Retrieval-Augmented Generation). The system automatically transcribes audio/video using OpenAI Whisper, chunks content, generates embeddings, and stores them in Pinecone for semantic search. Features include real-time streaming responses, document summarization, timestamp extraction for media playback, JWT authentication, Redis caching, and comprehensive CI/CD pipelines.

## Architecture

```
┌─────────┐
│ Browser │
└────┬────┘
     │ HTTP/SSE
     ▼
┌─────────────┐
│   FastAPI   │◄──────┐
│   Backend   │       │
└──┬──┬──┬──┬┘       │
   │  │  │  │         │
   │  │  │  └─────────┼──► OpenAI API (GPT-4o, Whisper, Embeddings)
   │  │  │            │
   │  │  └────────────┼──► Pinecone (Vector DB)
   │  │               │
   │  └───────────────┼──► Redis (Cache + Rate Limiting)
   │                  │
   └──────────────────┴──► PostgreSQL (Metadata, Users, Sessions)
```

## Features

### Core Features
- ✅ **PDF Upload & Processing** — Extract text from PDF documents with PyPDF2
- ✅ **Audio/Video Upload** — Transcribe MP3, WAV, M4A, MP4 files using OpenAI Whisper
- ✅ **AI Q&A Chatbot** — Ask questions about uploaded content, powered by GPT-4o
- ✅ **Document Summarization** — Generate concise summaries of documents and transcripts
- ✅ **Timestamp Extraction** — Extract and display timestamps from transcribed media
- ✅ **Media Playback with Seek** — Click timestamps to jump to specific moments in audio/video

### Advanced Features
- ✅ **Vector Search (Pinecone)** — Semantic search using text-embedding-3-small
- ✅ **SSE Streaming** — Real-time token-by-token response streaming
- ✅ **JWT Authentication** — Secure access + refresh token flow
- ✅ **Redis Caching** — Cache embeddings and frequently accessed data
- ✅ **Rate Limiting** — Prevent API abuse with Redis-backed rate limiting
- ✅ **Docker Compose** — One-command deployment with all services
- ✅ **CI/CD Pipelines** — Automated testing and deployment via GitHub Actions

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.11 + FastAPI | Async REST API with automatic OpenAPI docs |
| **Frontend** | React 18 + Tailwind CSS | Modern SPA with responsive design |
| **Database** | PostgreSQL 15 | User accounts, documents, chat sessions metadata |
| **Vector DB** | Pinecone | Semantic search over document embeddings |
| **Cache** | Redis 7 | Session cache, rate limiting, embedding cache |
| **AI/LLM** | OpenAI GPT-4o | Natural language understanding and generation |
| **Embeddings** | text-embedding-3-small | 1536-dim vectors for semantic search |
| **Transcription** | OpenAI Whisper (via API) | Audio/video to text transcription |
| **Container** | Docker + Docker Compose | Reproducible multi-service deployment |
| **CI/CD** | GitHub Actions | Automated testing, linting, and deployment |

## Prerequisites

- **Docker Desktop** (v20.10+) — [Download here](https://www.docker.com/products/docker-desktop)
- **OpenAI API Key** — Paid account required for GPT-4o and Whisper ([Get key](https://platform.openai.com/api-keys))
- **Pinecone Account** — Free tier works ([Sign up](https://www.pinecone.io/))
- **Git** — For cloning the repository

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/docqa.git
cd docqa
```

### 2. Navigate to project root
```bash
cd docqa
```

### 3. Copy environment template
```bash
cp backend/.env.example backend/.env
```

### 4. Fill in environment variables
Edit `backend/.env` and set the following **required** keys:
- `SECRET_KEY` — Generate with `openssl rand -hex 32`
- `OPENAI_API_KEY` — From OpenAI dashboard
- `PINECONE_API_KEY` — From Pinecone console
- `PINECONE_ENVIRONMENT` — Your Pinecone region (e.g., `us-east-1`)

Optional: Adjust `DATABASE_URL`, `REDIS_URL`, `ALLOWED_ORIGINS` if needed.

### 5. Start all services
```bash
docker compose up --build
```

This command will:
- Build backend and frontend Docker images
- Start PostgreSQL, Redis, backend API, and frontend dev server
- Run database migrations automatically via the migrator service
- Expose services on localhost
- Automatically create Pinecone index if it doesn't exist

### 6. Open the application
Navigate to **http://localhost:3000** in your browser.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs (DEBUG=true only) |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ Yes | — | JWT signing key (use `openssl rand -hex 32`) |
| `DEBUG` | No | `false` | Enable debug mode and API docs |
| `DATABASE_URL` | ✅ Yes | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis connection string |
| `PINECONE_API_KEY` | ✅ Yes | — | Pinecone API key |
| `PINECONE_ENVIRONMENT` | ✅ Yes | — | Pinecone region (e.g., `us-east-1`) |
| `PINECONE_INDEX_NAME` | No | `docqa-index` | Pinecone index name |
| `OPENAI_API_KEY` | ✅ Yes | — | OpenAI API key |
| `OPENAI_CHAT_MODEL` | No | `gpt-4o` | OpenAI chat model |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-small` | OpenAI embedding model |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` | CORS allowed origins (JSON array or comma-separated) |
| `MAX_FILE_SIZE_MB` | No | `50` | Maximum upload file size in MB |
| `ALLOWED_EXTENSIONS` | No | `["pdf","mp3","mp4",...]` | Allowed file extensions |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token expiration |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | JWT refresh token expiration |

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| **POST** | `/api/v1/auth/register` | No | Register new user account |
| **POST** | `/api/v1/auth/login` | No | Login and receive access + refresh tokens |
| **POST** | `/api/v1/auth/refresh` | No | Refresh access token using refresh token |
| **GET** | `/api/v1/auth/me` | Yes | Get current user profile |
| **POST** | `/api/v1/documents/upload` | Yes | Upload document or media file |
| **GET** | `/api/v1/documents/` | Yes | List all user documents |
| **GET** | `/api/v1/documents/{id}` | Yes | Get document details and metadata |
| **DELETE** | `/api/v1/documents/{id}` | Yes | Delete document and associated data |
| **POST** | `/api/v1/chat/` | Yes | Send chat message (supports SSE streaming) |
| **GET** | `/api/v1/chat/sessions` | Yes | List all chat sessions for user |
| **GET** | `/api/v1/chat/sessions/{id}` | Yes | Get session with full message history |
| **GET** | `/api/v1/health/` | No | Basic health check |
| **GET** | `/api/v1/health/ready` | No | Readiness check (DB + Redis) |

## Running Tests

### Backend Tests
```bash
cd backend
pip install -r requirements.txt
pytest tests/ --cov=app --cov-report=term-missing -v
```

**Expected output:** Coverage >= 95%

### Frontend Tests
```bash
cd frontend
npm install
npm run test
```

## Project Structure

```
docqa/
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/                   # API route handlers
│   │   │   ├── auth.py               # Authentication endpoints
│   │   │   ├── chat.py               # Chat and Q&A endpoints
│   │   │   ├── documents.py          # Document upload/management
│   │   │   ├── health.py             # Health check endpoints
│   │   │   └── router.py             # Main API router
│   │   ├── core/                     # Core configuration and setup
│   │   │   ├── config.py             # Settings and environment variables
│   │   │   ├── database.py           # PostgreSQL connection and session
│   │   │   ├── redis.py              # Redis connection and utilities
│   │   │   ├── security.py           # JWT and password hashing
│   │   │   └── dependencies.py       # FastAPI dependency injection
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py               # User model
│   │   │   ├── document.py           # Document model
│   │   │   ├── chat.py               # Chat session and message models
│   │   │   ├── transcript.py         # Transcript model
│   │   │   └── timestamp_chunk.py    # Timestamp chunk model
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── user.py               # User schemas
│   │   │   ├── document.py           # Document schemas
│   │   │   └── chat.py               # Chat schemas
│   │   ├── services/                 # Business logic layer
│   │   │   ├── auth_service.py       # Authentication logic
│   │   │   ├── document_service.py   # Document processing orchestration
│   │   │   ├── chat_service.py       # Chat and RAG logic
│   │   │   ├── transcription_service.py  # Whisper transcription
│   │   │   ├── embedding_service.py  # OpenAI embeddings
│   │   │   ├── chunking_service.py   # Text chunking
│   │   │   └── file_service.py       # File I/O operations
│   │   ├── repositories/             # Database access layer
│   │   │   ├── user_repository.py    # User CRUD operations
│   │   │   ├── document_repository.py # Document CRUD operations
│   │   │   └── chat_repository.py    # Chat CRUD operations
│   │   ├── tasks/                    # Background task processing
│   │   │   └── processing_pipeline.py # Document processing pipeline
│   │   ├── utils/                    # Utility functions
│   │   │   └── logger.py             # Structured logging setup
│   │   └── main.py                   # FastAPI application factory
│   ├── alembic/                      # Database migrations
│   ├── tests/                        # Pytest test suite
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Backend Docker image
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── components/               # Reusable UI components
│   │   │   ├── auth/                 # Auth-related components
│   │   │   ├── chat/                 # Chat UI components
│   │   │   ├── documents/            # Document management UI
│   │   │   ├── layout/               # Layout components
│   │   │   ├── ui/                   # Generic UI components (buttons, spinners)
│   │   │   ├── MediaPlayer.jsx       # Audio/video player with seek
│   │   │   ├── SummaryPanel.jsx      # Document summary display
│   │   │   └── TimestampBadge.jsx    # Clickable timestamp badges
│   │   ├── pages/                    # Route-level page components
│   │   │   ├── LoginPage.jsx         # Login page
│   │   │   ├── RegisterPage.jsx      # Registration page
│   │   │   ├── DashboardPage.jsx     # Main dashboard
│   │   │   └── ChatPage.jsx          # Chat interface
│   │   ├── services/                 # API client functions
│   │   │   ├── api.js                # Axios instance with interceptors
│   │   │   ├── authService.js        # Auth API calls
│   │   │   ├── documentService.js    # Document API calls
│   │   │   └── chatService.js        # Chat API calls (SSE support)
│   │   ├── store/                    # Zustand state management
│   │   │   └── authStore.js          # Global auth state
│   │   ├── utils/                    # Utility functions
│   │   ├── App.jsx                   # Main app component with routing
│   │   └── main.jsx                  # React entry point
│   ├── package.json                  # Node dependencies
│   └── Dockerfile                    # Frontend Docker image
├── docker/                           # Additional Dockerfiles
├── .github/workflows/                # CI/CD pipelines
│   ├── ci.yml                        # Continuous integration
│   └── cd.yml                        # Continuous deployment
├── docker-compose.yml                # Multi-service orchestration
├── .env.example                      # Environment variable template
└── README.md                         # This file
```

## Key Design Decisions

### Why FastAPI over Django?
FastAPI provides native async/await support, automatic OpenAPI documentation, and superior performance for I/O-bound operations like API calls to OpenAI and Pinecone. Its dependency injection system and Pydantic validation reduce boilerplate while maintaining type safety.

### Why Pinecone over FAISS?
Pinecone is a managed vector database that handles scaling, replication, and availability automatically. FAISS requires manual index management, persistence, and doesn't support multi-tenancy (per-user namespaces) out of the box. For production workloads, Pinecone's reliability and ease of use outweigh FAISS's cost savings.

### Why fetch + ReadableStream over EventSource for SSE?
EventSource doesn't support custom headers (needed for JWT authentication) and has limited error handling. Using fetch with ReadableStream provides full control over request headers, allows streaming responses, and enables better error recovery with our token refresh queue.

### Why queue-based token refresh over simple retry?
When multiple concurrent requests receive 401 errors, a naive retry approach causes a "thundering herd" where each request attempts to refresh the token simultaneously. Our queue-based approach ensures only one refresh request is made, with other requests waiting for the result, preventing rate limiting and reducing API calls.

### Why background tasks for document processing?
Document processing (transcription, chunking, embedding, vector upsert) can take 30+ seconds for large files. Running these operations synchronously would block the upload endpoint and cause timeouts. Background tasks allow immediate response to the user while processing continues asynchronously, with status updates via polling or WebSocket.

### Why non-root Docker user?
Running containers as root violates the principle of least privilege and increases security risk. If an attacker exploits a vulnerability in the application, they gain root access to the container and potentially the host. Using a non-root user (UID 1000) limits the blast radius of potential security breaches.

## Known Limitations

- **OpenAI API costs money per request** — GPT-4o and Whisper are paid services. Monitor usage in the OpenAI dashboard to avoid unexpected bills. Consider implementing usage quotas per user.
- **Pinecone free tier has 1 index limit** — The free tier supports only one index. If you need multiple environments (dev/staging/prod), you'll need a paid plan or use namespaces to separate data. The application automatically creates the index on first run.
- **No horizontal scaling** — The current architecture uses a single upload volume and in-memory background tasks. For production scale, migrate to a distributed task queue (Celery + RabbitMQ) and object storage (S3).
- **ffmpeg must be in Docker image** — Video processing requires ffmpeg for audio extraction. The Docker image includes it, but local development requires manual installation (`apt install ffmpeg` or `brew install ffmpeg`).

## CI/CD

### GitHub Secrets

For local development, no GitHub secrets are required. When deploying via GitHub Actions:
- `GITHUB_TOKEN` is automatically provided by GitHub Actions
- Add your deployment-specific secrets (e.g., `DOCKER_REGISTRY_TOKEN`) in repository settings if needed

### Database Migrations

The application uses Alembic for database migrations:

```bash
# Create a new migration after model changes
cd backend
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

In Docker Compose, migrations run automatically via the `migrator` service before the backend starts.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using FastAPI, React, and OpenAI**


## DevOps & CI/CD

### GitHub Actions Workflows

This project includes two GitHub Actions workflows for automated testing and deployment:

#### 1. Continuous Integration (`.github/workflows/ci.yml`)
Runs on every push and pull request to validate code quality:
- **Backend**: Linting (flake8, black), type checking (mypy), unit tests (pytest), coverage reporting
- **Frontend**: Linting (ESLint), type checking (TypeScript), unit tests (Vitest), build validation
- **Docker**: Multi-stage build validation for both backend and frontend images

#### 2. Continuous Deployment (`.github/workflows/cd.yml`)
Deploys to staging/production on successful merge to `main`:
- Builds and tags Docker images
- Pushes images to container registry (Docker Hub, AWS ECR, or custom registry)
- Deploys to target environment using Docker Compose or Kubernetes
- Runs smoke tests to validate deployment

### Required GitHub Secrets

Configure the following secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

#### Core Application Secrets
| Secret Name | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | ✅ Yes | JWT signing key for authentication | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for GPT-4o and Whisper | `sk-proj-...` |
| `PINECONE_API_KEY` | ✅ Yes | Pinecone API key for vector database | `pcsk_...` |
| `PINECONE_ENVIRONMENT` | ✅ Yes | Pinecone region/environment | `us-east-1` |
| `PINECONE_INDEX_NAME` | No | Pinecone index name (defaults to `docqa-index`) | `docqa-prod` |

#### Database & Cache Secrets
| Secret Name | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `POSTGRES_USER` | ✅ Yes | PostgreSQL username | `docqa_user` |
| `POSTGRES_PASSWORD` | ✅ Yes | PostgreSQL password | `secure_password_here` |
| `POSTGRES_DB` | ✅ Yes | PostgreSQL database name | `docqa_prod` |
| `REDIS_URL` | No | Redis connection string (defaults to `redis://redis:6379/0`) | `redis://redis.example.com:6379/0` |

#### Container Registry Secrets
| Secret Name | Required | Description | Example |
|---|---|---|---|
| `DOCKER_REGISTRY_URL` | No | Custom registry URL (defaults to Docker Hub) | `registry.example.com` |
| `DOCKER_REGISTRY_USERNAME` | ✅ Yes* | Registry username | `myusername` |
| `DOCKER_REGISTRY_TOKEN` | ✅ Yes* | Registry access token or password | `dckr_pat_...` |
| `AWS_ACCESS_KEY_ID` | ✅ Yes** | AWS access key (if using ECR) | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | ✅ Yes** | AWS secret key (if using ECR) | `wJalrXUtn...` |
| `AWS_REGION` | ✅ Yes** | AWS region (if using ECR) | `us-east-1` |

\* Required if using Docker Hub or custom registry  
\** Required if using AWS ECR

#### Deployment Secrets
| Secret Name | Required | Description | Example |
|---|---|---|---|
| `DEPLOY_HOST` | No | Deployment server hostname | `prod.example.com` |
| `DEPLOY_SSH_KEY` | No | SSH private key for deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_USER` | No | SSH username for deployment | `deploy` |
| `SLACK_WEBHOOK_URL` | No | Slack webhook for deployment notifications | `https://hooks.slack.com/services/...` |

### Configuring Custom Container Registry

#### Docker Hub (Default)
```yaml
# .github/workflows/cd.yml
- name: Login to Docker Hub
  uses: docker/login-action@v2
  with:
    username: ${{ secrets.DOCKER_REGISTRY_USERNAME }}
    password: ${{ secrets.DOCKER_REGISTRY_TOKEN }}
```

#### AWS ECR
```yaml
# .github/workflows/cd.yml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v2
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ secrets.AWS_REGION }}

- name: Login to Amazon ECR
  id: login-ecr
  uses: aws-actions/amazon-ecr-login@v1
```

#### Custom Registry
```yaml
# .github/workflows/cd.yml
- name: Login to Custom Registry
  uses: docker/login-action@v2
  with:
    registry: ${{ secrets.DOCKER_REGISTRY_URL }}
    username: ${{ secrets.DOCKER_REGISTRY_USERNAME }}
    password: ${{ secrets.DOCKER_REGISTRY_TOKEN }}
```

### Local Development Setup

1. **Clone and configure environment:**
   ```bash
   git clone https://github.com/yourusername/docqa.git
   cd docqa
   cp .env.example .env
   # Edit .env with your local credentials
   ```

2. **Start services:**
   ```bash
   docker compose up --build
   ```

3. **Run tests locally:**
   ```bash
   # Backend tests (requires Docker for PostgreSQL container)
   cd backend
   pip install -r requirements.txt
   pytest tests/ --cov=app --cov-report=html -v
   
   # Frontend tests
   cd frontend
   npm install
   npm run test
   ```

### Production Deployment Checklist

- [ ] Set `DEBUG=false` in production environment
- [ ] Use strong `SECRET_KEY` (32+ random bytes)
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up database backups (automated daily snapshots)
- [ ] Configure log aggregation (CloudWatch, Datadog, or ELK stack)
- [ ] Set up monitoring and alerting (Prometheus + Grafana)
- [ ] Enable rate limiting in production (already configured via SlowAPI)
- [ ] Configure CORS origins to match production domain
- [ ] Set up CDN for frontend static assets (CloudFront, Cloudflare)
- [ ] Implement database connection pooling (already configured via SQLAlchemy)
- [ ] Configure Redis persistence (AOF or RDB snapshots)
- [ ] Set up container health checks (already configured in docker-compose.yml)
- [ ] Implement horizontal scaling (load balancer + multiple backend instances)
- [ ] Configure object storage for uploads (S3, MinIO, or Azure Blob)
- [ ] Set up secrets management (AWS Secrets Manager, HashiCorp Vault)

### Monitoring & Observability

The application includes built-in observability features:

- **Structured JSON logging** with request IDs for tracing
- **Health check endpoints** (`/api/v1/health/` and `/api/v1/health/ready`)
- **Docker health checks** for all services
- **Prometheus-compatible metrics** (can be added via `prometheus-fastapi-instrumentator`)
- **Request/response timing** logged for performance analysis
- **Error tracking** with full stack traces in logs (never exposed to clients)

### Troubleshooting CI/CD

#### Tests failing in CI but passing locally
- Ensure PostgreSQL test container is available (requires Docker in CI environment)
- Set `USE_POSTGRES_TESTS=false` to fallback to SQLite for environments without Docker
- Check that all required secrets are configured in GitHub repository settings

#### Docker build failures
- Verify Dockerfile paths are correct relative to build context
- Check that all dependencies are pinned to specific versions
- Ensure multi-stage builds are properly configured

#### Deployment failures
- Verify SSH keys have correct permissions (600)
- Check that deployment host is reachable from GitHub Actions runners
- Validate that all required secrets are set and not expired
- Review deployment logs in GitHub Actions workflow runs

### Security Best Practices

- **Never commit secrets** to version control (use `.env` files and `.gitignore`)
- **Rotate secrets regularly** (every 90 days minimum)
- **Use least-privilege IAM roles** for AWS deployments
- **Enable 2FA** on all service accounts (GitHub, Docker Hub, AWS)
- **Scan Docker images** for vulnerabilities (Trivy, Snyk, or AWS ECR scanning)
- **Implement network policies** in Kubernetes to restrict pod-to-pod communication
- **Use secrets management** tools instead of environment variables in production
- **Enable audit logging** for all production systems
- **Implement RBAC** for database and Redis access
- **Use read-only file systems** in containers where possible
