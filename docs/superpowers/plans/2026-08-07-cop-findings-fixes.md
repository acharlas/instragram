# Cop-Findings Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the findings that matter for a PORTFOLIO/POC project (few viewers, demo-focused): the critical session-refresh write-back bug (users force-logged-out ~15 min after login — breaks the demo itself), dishonest logout reporting, and the private-account leak in follower lists. Env/infra hardening (Tasks 2, 5, 6) is deliberately dropped — for a localhost demo, `APP_ENV=local` + insecure cookies are correct, and `.dockerignore`/healthchecks are irrelevant to the showcase.

**Architecture:** 3 independent tasks. Task 1 is the critical fix: route session rotation through next-auth's HTTP `/api/auth/session` from middleware so the re-encoded JWT cookie actually reaches the browser (RSC `getServerSession` discards `Set-Cookie` — verified in `node_modules/next-auth/next/index.js:143`). Tasks 3-4 are small behavior fixes with tests. All commits on a new branch `chore/cop-fixes` (branched from current `chore/security-hardening` HEAD, unmerged).

**Tech Stack:** Next.js 15 + next-auth 4 middleware, FastAPI backend, vitest + pytest.

**Dropped from plan (POC scope):** env flip (`APP_ENV` override, was Task 2 — localhost demo wants `local`), `.dockerignore` (was Task 5), healthchecks + depends_on gating (was Task 6).

**Deferred (documented, not fixed — portfolio scale):** unbounded `limit=None` list endpoints (authenticated DoS), upload size pre-check before multipart parse, case-insensitive usernames, login timing oracle, refresh-rotation deadlock, notification-stream anti-join cost, explore-feed OFFSET scans, `lower(username)` functional index, redundant unique+index pairs, FK-cascade app cleanup, process-local refresh dedup, `NEXTAUTH_URL`/tunnel config (user action if ever deployed publicly).

---

### Task 0: Branch + plan doc

- [ ] **Step 1: Create branch and save plan**

```bash
cd /home/alex/MyStagram && git checkout -b chore/cop-fixes
mkdir -p docs/superpowers/plans
# save this file to docs/superpowers/plans/2026-08-07-cop-findings-fixes.md
git add docs/superpowers/plans/2026-08-07-cop-findings-fixes.md
git commit -m "docs: save cop-findings fixes plan"
```

---

### Task 1: Session refresh write-back (critical)

**Files:**
- Modify: `frontend/src/middleware.ts`
- Test: `frontend/src/tests/auth/middleware.test.ts`

- [ ] **Step 1: Write the failing tests (append a new describe block to `frontend/src/tests/auth/middleware.test.ts`)**

```ts
describe("middleware session cookie sync", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards refreshed session cookies from the session route when token is recoverable", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-token",
      accessTokenExpires: Date.now() - 1_000,
      refreshToken: "refresh-token",
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("{}", {
        headers: [
          ["set-cookie", "next-auth.session-token=rotated-jwt; Path=/; HttpOnly"],
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost/api/auth/session",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(response?.headers.get("set-cookie")).toContain("rotated-jwt");
    expect(response?.status).toBe(200);
  });

  it("does not touch the session route when the access token is usable", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "valid-token",
      accessTokenExpires: Date.now() + 60_000,
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response?.status).toBe(200);
  });

  it("keeps serving the page when the session sync fails", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-token",
      accessTokenExpires: Date.now() - 1_000,
      refreshToken: "refresh-token",
    });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(200);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/auth/middleware.test.ts`
Expected: the 3 new tests FAIL (no fetch call, no set-cookie forwarded); the 12 existing tests still pass.

- [ ] **Step 3: Implement — modify `frontend/src/middleware.ts`**

Add this helper above `middleware`:

```ts
async function syncSessionCookie(request: NextRequest, response: NextResponse) {
  try {
    const sessionResponse = await fetch(
      new URL("/api/auth/session", request.url),
      {
        headers: { cookie: request.headers.get("cookie") ?? "" },
        cache: "no-store",
      },
    );
    for (const cookie of sessionResponse.headers.getSetCookie()) {
      response.headers.append("set-cookie", cookie);
    }
  } catch {
    // ponytail: transient failure — next navigation retries; never block the page.
  }
}
```

Replace the tail of `middleware`:

```ts
  const token = await readSessionToken(request);
  const sessionState = getSessionState(token);
  if (sessionState === "invalid") {
    return NextResponse.redirect(buildLoginRedirect(request));
  }

  const response = NextResponse.next();
  if (sessionState === "recoverable") {
    // Rotation must run through next-auth's HTTP route: the RSC path
    // (getServerSession) discards Set-Cookie, so in-memory rotation leaves
    // the browser holding a revoked refresh token and the session dies.
    await syncSessionCookie(request, response);
  }
  return response;
```

Note: if the test environment's `Response.headers.getSetCookie` is unavailable (Node < 19.7), fall back in the helper to `[sessionResponse.headers.get("set-cookie")]` filtered for non-null.

- [ ] **Step 4: Run tests + build**

Run: `cd frontend && npx vitest run src/tests/auth/middleware.test.ts && npm run build`
Expected: all 15 middleware tests pass; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/middleware.ts frontend/src/tests/auth/middleware.test.ts
git commit -m "fix(auth): persist rotated session cookie via middleware -> HTTP session route"
```

### Task 2: Honest logout reporting

**Files:**
- Modify: `frontend/src/app/api/logout/route.ts`
- Test: `frontend/src/tests/auth/logout-route.test.ts`

- [ ] **Step 1: Update the outdated test and add a failure test (edit `frontend/src/tests/auth/logout-route.test.ts`)**

Replace the test `"keeps local logout successful when backend revoke fails"` with:

```ts
  it("reports failure when backend revocation fails", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "access-token",
      refreshToken: "refresh-token",
    });
    apiServerFetchMock.mockRejectedValueOnce(
      new ApiError(503, "Service unavailable"),
    );

    const response = await POST(new Request("http://localhost/api/logout"));
    const payload = (await response.json()) as {
      success?: boolean;
      revoked?: boolean;
      detail?: string | null;
    };

    expect(response.status).toBe(502);
    expect(payload.success).toBe(false);
    expect(payload.revoked).toBe(false);
    expect(payload.detail).toBe("Service unavailable");
  });

  it("reports failure on unexpected errors", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "access-token",
      refreshToken: "refresh-token",
    });
    apiServerFetchMock.mockRejectedValueOnce(new TypeError("network down"));

    const response = await POST(new Request("http://localhost/api/logout"));
    const payload = (await response.json()) as { success?: boolean };

    expect(response.status).toBe(502);
    expect(payload.success).toBe(false);
  });
```

- [ ] **Step 2: Run the tests to verify the new ones fail**

Run: `cd frontend && npx vitest run src/tests/auth/logout-route.test.ts`
Expected: the two rewritten tests FAIL (route still returns 200/success).

- [ ] **Step 3: Implement — modify `frontend/src/app/api/logout/route.ts`**

Replace the error handling block:

```ts
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return NextResponse.json({ success: true, revoked: false });
      }
      return NextResponse.json(
        {
          success: false,
          revoked: false,
          detail: error.message ?? null,
        },
        { status: 502 },
      );
    }
    console.error("Unexpected error during logout", error);
    return NextResponse.json(
      {
        success: false,
        revoked: false,
        detail: "Unexpected error",
      },
      { status: 502 },
    );
  }
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run src/tests/auth/logout-route.test.ts`
Expected: all 4 logout tests pass (2 unchanged + 2 rewritten).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/api/logout/route.ts frontend/src/tests/auth/logout-route.test.ts
git commit -m "fix(auth): report logout revocation failures honestly (502, success=false)"
```

### Task 3: Hide private accounts from follower/following lists

**Files:**
- Modify: `backend/api/v1/users.py` (list_followers ~line 696, list_following ~line 753)
- Test: `backend/tests/test_follow.py`

- [ ] **Step 1: Write the failing test (append to `backend/tests/test_follow.py`)**

```python
@pytest.mark.asyncio
async def test_private_users_hidden_from_follower_lists(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    public_payload = make_user_payload("public_user")
    private_payload = make_user_payload("private_user")
    stranger_payload = make_user_payload("stranger")

    public_user = (
        await async_client.post("/api/v1/auth/register", json=public_payload)
    ).json()
    private_user = (
        await async_client.post("/api/v1/auth/register", json=private_payload)
    ).json()
    stranger = (
        await async_client.post("/api/v1/auth/register", json=stranger_payload)
    ).json()

    # Make the private user private, then have them follow the public user.
    await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": private_payload["username"],
            "password": private_payload["password"],
        },
    )
    assert (
        await async_client.patch("/api/v1/me", data={"is_private": "true"})
    ).status_code == 200
    assert (
        await async_client.post(
            f"/api/v1/users/{public_user['username']}/follow"
        )
    ).status_code == 200

    # A stranger viewing the public user's followers must not see the private user.
    await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": stranger_payload["username"],
            "password": stranger_payload["password"],
        },
    )
    followers_resp = await async_client.get(
        f"/api/v1/users/{public_user['username']}/followers"
    )
    assert followers_resp.status_code == 200
    follower_names = {f["username"] for f in followers_resp.json()}
    assert private_user["username"] not in follower_names

    # A follower of the private user can see them in the list.
    db_session.add(
        Follow(
            follower_id=public_user["id"],
            followee_id=private_user["id"],
        )
    )
    await db_session.commit()

    await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": stranger_payload["username"],
            "password": stranger_payload["password"],
        },
    )
    followers_resp = await async_client.get(
        f"/api/v1/users/{public_user['username']}/followers"
    )
    assert followers_resp.status_code == 200
    follower_names = {f["username"] for f in followers_resp.json()}
    assert private_user["username"] in follower_names
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_follow.py::test_private_users_hidden_from_follower_lists -q`
Expected: FAIL — private username present in the stranger's follower list.

- [ ] **Step 3: Implement — modify `backend/api/v1/users.py`**

Add the import (with the existing `from services.account_blocks import (...)` block):

```python
from services.post_policy import build_author_view_filter
```

In `list_followers`, replace this filter:

```python
        .where(
            _eq(Follow.followee_id, target_user_id),
            build_not_blocked_either_direction_filter(
                viewer_id=current_user_id,
                candidate_user_id_column=cast(ColumnElement[str], User.id),
            ),
        )
```

with:

```python
        .where(
            _eq(Follow.followee_id, target_user_id),
            build_author_view_filter(
                viewer_id=current_user_id,
                post_author_column=cast(ColumnElement[str], User.id),
                author_is_private_column=cast(ColumnElement[bool], User.is_private),
            ),
        )
```

In `list_following`, replace this filter:

```python
        .where(
            _eq(Follow.follower_id, target_user_id),
            build_not_blocked_either_direction_filter(
                viewer_id=current_user_id,
                candidate_user_id_column=cast(ColumnElement[str], User.id),
            ),
        )
```

with the same filter shape, replacing `build_not_blocked_either_direction_filter`:

```python
        .where(
            _eq(Follow.follower_id, target_user_id),
            build_author_view_filter(
                viewer_id=current_user_id,
                post_author_column=cast(ColumnElement[str], User.id),
                author_is_private_column=cast(ColumnElement[bool], User.is_private),
            ),
        )
```

Note: `build_author_view_filter` already includes the either-direction block filter, so it fully replaces the removed one in both endpoints.

- [ ] **Step 4: Run the test + full backend suite**

Run: `cd backend && uv run pytest tests/test_follow.py -q && uv run pytest -q`
Expected: new test passes; all 224+ backend tests pass (follower/following list tests in `test_follow.py:81-120` still pass — members are public in those fixtures).

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/users.py backend/tests/test_follow.py
git commit -m "fix(privacy): hide private accounts from follower/following lists"
```

### Task 4: Final verification

- [ ] **Run both suites:**
```bash
cd backend && uv run pytest -q
cd ../frontend && npm run test
```
Expected: all backend and all frontend tests pass.

- [ ] **Update plan checkboxes** and record session state.

**Deferred (deliberate — see Goal section):** unbounded list endpoints, upload pre-parse size cap, case-insensitive usernames, login timing oracle, rotation deadlock, stream query cost, explore OFFSET, `lower(username)` index, redundant indexes, FK-cascade app cleanup, multi-worker refresh dedup, env/infra hardening (`APP_ENV`, `.dockerignore`, healthchecks), `NEXTAUTH_URL` for any future public deployment.
