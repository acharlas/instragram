# Instragram Core Clone

Instragram is a one-week build that recreates the core Instagram experience (feed, posts, likes, comments, follows) with a security-first, production-ready architecture. Everything runs locally via Docker Compose and focuses on clean separation between a FastAPI backend, a Next.js frontend, and managed infrastructure services.

---

## Tech Stack

- **Frontend**: Next.js 14 App Router (TypeScript), TailwindCSS, Zod, NextAuth, Playwright
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, asyncpg, Redis, MinIO, pytest, httpx, factory_boy, Ruff, mypy
- **Database**: PostgreSQL 16
- **Infrastructure**: Docker Compose, Redis, MinIO, Traefik (optional reverse proxy), MIT License

---

## Service Overview

| Service  | Port | Description |
|----------|------|-------------|
| frontend | 3000 | Next.js App Router client/UI |
| backend  | 8000 | FastAPI REST API (`/api/v1`) |
| postgres | 5432 | Primary relational database |
| redis    | 6379 | Rate limiting + cache |
| minio    | 9000 | S3-compatible object storage + signed URLs |

> All services are local-only. No external network access is required.

---

## Repository Layout

```
.
├── backend/            # FastAPI application package and tooling
├── frontend/           # Next.js project
├── docker-compose.yml  # Local runtime orchestration
├── .env.backend        # Backend configuration (loaded by Docker and app)
├── .env.frontend       # Frontend configuration (Next.js runtime)
└── README.md           # Project documentation (this file)
```

Additional backend scaffolding (modules, routers, tests) is introduced as part of the initial setup and will expand as features land.

---

## Environment Configuration

The stack relies on two environment files at the repository root:

- `.env.backend`
  - `APP_ENV`: Deployment environment (`local`, `staging`, `prod`)
  - `SECRET_KEY`: FastAPI JWT signing secret (change in production)
  - `DATABASE_URL`: Async SQLAlchemy DSN (`postgresql+asyncpg://...`)
  - `REDIS_URL`: Redis connection string
  - `MINIO_*`: S3-compatible credentials for MinIO
  - `JWT_ALGORITHM`: Signing algorithm (`HS256` default)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime (minutes)
  - `REFRESH_TOKEN_EXPIRE_MINUTES`: Refresh token lifetime (minutes)

- `.env.frontend`
  - Next.js runtime configuration (e.g., `NEXT_PUBLIC_API_URL`, NextAuth secrets). Add keys here before running the app.

These files are consumed by Docker Compose and by local tooling. Do **not** commit production secrets.

---

## Getting Started

### 1. Install prerequisites

- Docker Desktop (or Docker Engine + Docker Compose v2)
- Make sure ports 3000, 8000, 5432, 6379, and 9000 are free

### 2. Boot the stack

```bash
docker compose up --build
```

Once containers are healthy:

- Backend API docs: http://localhost:8000/docs
- Frontend web app: http://localhost:3000
- MinIO console: http://localhost:9001 (credentials from `.env.backend`)

To stop everything:

```bash
docker compose down
```

Add `-v` to remove local volumes if you need a clean reset.

---

## Local Development

### Backend (FastAPI)

```bash
cd backend
uv sync           # install dependencies (requires uv)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Run tests: `uv run pytest`
- Static analysis: `uv run ruff check .`, `uv run mypy .`
- Format: `uv run ruff format .`

Database migrations use Alembic; the command scaffolding will be introduced alongside the migration setup (`uv run alembic upgrade head`).

### Frontend (Next.js)

```bash
cd frontend
pnpm install
pnpm dev
```

- Lint: `pnpm lint`
- Tests: `pnpm test` (Jest/unit) and `pnpm e2e` (Playwright)

---

## Security Posture

- Argon2id password hashing with high memory cost
- JWT access tokens (15 minutes) + refresh tokens (7 days) with rotation and revocation
- HttpOnly, Secure, SameSite=Lax cookies for session transport
- Strict CORS allow-list limited to localhost origins
- Redis-backed rate limits (login 5/min, post 3/min, comment 10/min, like 60/min)
- HSTS, `X-Content-Type-Options`, `X-Frame-Options=DENY`
- MinIO private bucket with signed URL delivery
- Media sanitizer pipeline (Pillow re-encode, EXIF stripping)

Each security control has corresponding unit/integration coverage to prevent regressions.

---

## Testing Strategy

- **Backend**
  - Unit tests for domain logic and services (pytest + factory_boy)
  - Integration tests for API endpoints (httpx AsyncClient)
  - Coverage enforced via `pytest --cov`
- **Frontend**
  - Component/unit tests via React Testing Library
  - e2e flows with Playwright hitting Dockerized backend
- **CI (future)**
  - Lint → type check → backend tests → frontend tests → e2e smoke suite

---

## Roadmap Snapshot

1. Scaffold FastAPI project structure with modular routers, dependency wiring, and configuration management (next step).
2. Implement authentication (register/login/refresh/logout) with JWT cookie transport.
3. Build user profile endpoints and follow graph.
4. Deliver post creation, media uploads, comments, and likes.
5. Implement homepage feed and search.
6. Add Playwright coverage for core user journeys.

---

## License

This project is released under the MIT License. See `LICENSE` for details.

---

Need help or want to propose changes? Open an issue or start a discussion in the repo.
