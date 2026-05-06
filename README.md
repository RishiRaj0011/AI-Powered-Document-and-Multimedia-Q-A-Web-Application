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
