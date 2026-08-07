# Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the HIGH-severity findings from the security audit of MyStagram: outdated/vulnerable frontend deps, missing security headers, prod-exposed API docs, root containers with dev deps in prod images, and a dead backend dependency.

**Architecture:** 7 independent tasks — 2 dependency bumps (frontend), 1 config change each for Next.js headers and FastAPI docs, 1 dep removal (backend), 2 Dockerfile hardenings. Each task commits separately and verifies with existing test suites; the two Docker tasks verify via `docker compose build`. No runtime code paths change.

**Tech Stack:** Next.js 15 + next-auth 4 (frontend), FastAPI + SQLAlchemy + uv (backend), vitest + pytest, Docker Compose.

**Deferred (deliberate — YAGNI for a portfolio project):** PyJWT swap (jose 3.5.0 is CVE-fixed), refresh-token reuse detection, nonce-based CSP (breaks Next inline scripts without middleware infra; basic headers cover the showcase), cloudflared version pin, uuid bump (bounds-check only, no attack path here).

---

### Task 1: Bump next to 15.5.23

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`

- [ ] **Step 1: Install the patched Next.js**

```bash
cd frontend && npm install next@15.5.23
```

- [ ] **Step 2: Verify advisories cleared**

```bash
npm audit --omit=dev
```
Expected: sharp/libvips and Next.js advisories gone; only `uuid` moderate may remain (deferred).

- [ ] **Step 3: Verify build and full suite**

```bash
npm run build && npm run test
```
Expected: build succeeds, all vitest suites pass (middleware/auth tests exercise the patched paths).

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix(deps): bump next to 15.5.23 to close CVEs (RCE, middleware bypass, cache poisoning)"
```

### Task 2: Move vitest to devDependencies and bump to ^4.1.0

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`

- [ ] **Step 1: Edit `frontend/package.json`** — remove `"vitest": "^4.0.3"` from `dependencies`, add to `devDependencies`:

```json
"vitest": "^4.1.0"
```

- [ ] **Step 2: Regenerate lockfile and apply residual fixes**

```bash
cd frontend && npm install && npm audit fix
```
Expected: no errors; rollup path-traversal advisory resolved (rollup is a vitest dependency).

- [ ] **Step 3: Verify tests still pass**

```bash
npm run test
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix(deps): move vitest to devDeps, bump to ^4.1.0 (GHSA-5xrq-8626-4rwp)"
```

### Task 3: Add security headers to Next.js

**Files:**
- Modify: `frontend/next.config.ts`
- Create: `frontend/tests/config/next-config.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { securityHeaders } from "../../../next.config";

describe("next config security headers", () => {
  it("sets nosniff", () => {
    expect(securityHeaders).toContainEqual({
      key: "X-Content-Type-Options",
      value: "nosniff",
    });
  });
  it("denies framing", () => {
    expect(securityHeaders).toContainEqual({
      key: "X-Frame-Options",
      value: "DENY",
    });
  });
  it("sets strict referrer policy", () => {
    expect(securityHeaders).toContainEqual({
      key: "Referrer-Policy",
      value: "strict-origin-when-cross-origin",
    });
  });
  it("disables intrusive permissions", () => {
    expect(securityHeaders).toContainEqual({
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=()",
    });
  });
  it("enables HSTS", () => {
    expect(securityHeaders).toContainEqual({
      key: "Strict-Transport-Security",
      value: "max-age=31536000; includeSubDomains",
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/config/next-config.test.ts`
Expected: FAIL with `securityHeaders is not exported`.

- [ ] **Step 3: Implement — replace `frontend/next.config.ts`**

```ts
import type { NextConfig } from "next";

export const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "4mb",
    },
  },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
```

- [ ] **Step 4: Run test + build to verify**

Run: `cd frontend && npx vitest run tests/config/next-config.test.ts && npm run build`
Expected: PASS, build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/next.config.ts frontend/tests/config/next-config.test.ts
git commit -m "feat(security): add security headers (nosniff, XFO, HSTS, referrer, permissions-policy)"
```

### Task 4: Gate API docs to non-production envs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_startup_contract.py` (append test)

- [ ] **Step 1: Write the failing test (append to `backend/tests/test_startup_contract.py`)**

```python
def test_docs_disabled_outside_local_and_test() -> None:
    from core.config import settings
    from app.main import create_app

    original_env = settings.app_env
    try:
        settings.app_env = "production"
        app = create_app()
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    finally:
        settings.app_env = original_env
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_startup_contract.py::test_docs_disabled_outside_local_and_test -q`
Expected: FAIL (assertions on `None`).

- [ ] **Step 3: Implement — edit `backend/app/main.py`**

```python
show_docs = settings.app_env.strip().lower() in {"local", "test"}
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs" if show_docs else None,
    redoc_url="/redoc" if show_docs else None,
    openapi_url="/openapi.json" if show_docs else None,
)
```

- [ ] **Step 4: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (no existing test references docs; local env keeps them).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_startup_contract.py
git commit -m "fix(security): disable API docs outside local/test envs"
```

### Task 5: Remove dead passlib dependency

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock`

- [ ] **Step 1: Edit `backend/pyproject.toml`** — remove the line `"passlib[bcrypt]>=1.7.4",`

- [ ] **Step 2: Regenerate lockfile and verify no imports remain**

```bash
cd backend && uv lock && uv sync && grep -rn "passlib" --include="*.py" . | grep -v ".venv"
```
Expected: grep output empty; sync succeeds.

- [ ] **Step 3: Run backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(deps): remove unused passlib"
```

### Task 6: Harden backend Docker image

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Replace `backend/Dockerfile` with:**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

ENV UV_PROJECT_ENVIRONMENT=/opt/uv
ENV PATH="/opt/uv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app /opt/uv
USER appuser

CMD ["./scripts/start.sh"]
```

Note: `start.sh` keeps `uv run` for the avatar/prune scripts — `uv run` is a no-op re-sync here (same pyproject/uv.lock, writable env and cache), so the non-root user is safe.

- [ ] **Step 2: Verify container contract test + build**

Run: `cd backend && python -m pytest tests/test_startup_contract.py::test_dockerfile_uses_single_startup_script -q && cd .. && docker compose build backend`
Expected: PASS; build completes.

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "fix(docker): run backend as non-root, drop dev extras from prod image"
```

### Task 7: Harden frontend Docker image (multi-stage)

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Replace `frontend/Dockerfile` with:**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/package.json /app/package-lock.json ./
RUN npm ci --omit=dev
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts
USER node
CMD ["npm", "run", "start"]
```

- [ ] **Step 2: Build and smoke-test**

```bash
docker compose build frontend && docker compose up -d frontend
sleep 5 && curl -sI http://localhost:80 | head -5
docker exec $(docker compose ps -q frontend) whoami
```
Expected: HTTP 200 response; `whoami` prints `node`.

- [ ] **Step 3: Commit**

```bash
git add frontend/Dockerfile
git commit -m "fix(docker): multi-stage frontend image, non-root, prod deps only"
```

### Task 8: Final verification

- [ ] **Run both suites + audits:**
```bash
cd backend && python -m pytest -q && cd ../frontend && npm run test && npm audit --omit=dev
```
Expected: all pass; audit clean except deferred `uuid` moderate.
- [ ] **Verify compose config still valid:** `docker compose config -q`
- [ ] If any Docker task failed in CI-less env, note it as a follow-up rather than reverting.
