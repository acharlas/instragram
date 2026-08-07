import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const getTokenMock = vi.hoisted(() => vi.fn());

vi.mock("next-auth/jwt", () => ({
  getToken: getTokenMock,
}));

import { config, middleware } from "../../middleware";

function buildJwtWithExp(exp: number): string {
  const header = Buffer.from(
    JSON.stringify({ alg: "HS256", typ: "JWT" }),
  ).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
  return `${header}.${payload}.signature`;
}

describe("middleware token expiry checks", () => {
  it("redirects to login when access token is expired and no refresh token is available", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-token",
      accessTokenExpires: Date.now() - 1_000,
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toContain("/login");
  });

  it("accepts requests with non-expired access token", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "valid-token",
      accessTokenExpires: Date.now() + 60_000,
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(200);
  });

  it("falls back to JWT exp when accessTokenExpires is missing", async () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const expiredJwt = buildJwtWithExp(nowSeconds - 30);
    getTokenMock.mockResolvedValueOnce({
      accessToken: expiredJwt,
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toContain("/login");
  });

  it("allows expired access token when refresh token is present", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-token",
      accessTokenExpires: Date.now() - 1_000,
      refreshToken: "refresh-token",
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(200);
  });

  it("keeps login page accessible when only refresh token exists", async () => {
    getTokenMock.mockResolvedValueOnce({
      refreshToken: "refresh-token",
    });

    const response = await middleware(
      new NextRequest("http://localhost/login"),
    );

    expect(response?.status).toBe(200);
  });

  it("allows protected routes when only refresh token exists", async () => {
    getTokenMock.mockResolvedValueOnce({
      refreshToken: "refresh-token",
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(200);
  });

  it("redirects to login when token has terminal error", async () => {
    getTokenMock.mockResolvedValueOnce({
      refreshToken: "refresh-token",
      error: "RefreshAccessTokenError",
    });

    const response = await middleware(new NextRequest("http://localhost/"));

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toContain("/login");
  });

  it("keeps login accessible when refresh token exists but access token is expired", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-token",
      accessTokenExpires: Date.now() - 1_000,
      refreshToken: "refresh-token",
    });

    const response = await middleware(
      new NextRequest("http://localhost/login"),
    );

    expect(response?.status).toBe(200);
  });

  it("redirects authenticated users away from login page", async () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const validJwt = buildJwtWithExp(nowSeconds + 60);
    getTokenMock.mockResolvedValueOnce({
      accessToken: validJwt,
      accessTokenExpires: Date.now() + 60_000,
    });

    const response = await middleware(
      new NextRequest("http://localhost/login"),
    );

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toContain("/");
  });

  it("redirects authenticated users away from register page", async () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const validJwt = buildJwtWithExp(nowSeconds + 60);
    getTokenMock.mockResolvedValueOnce({
      accessToken: validJwt,
      accessTokenExpires: Date.now() + 60_000,
    });

    const response = await middleware(
      new NextRequest("http://localhost/register"),
    );

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toContain("/");
  });

  it("excludes internal API routes from middleware matcher", () => {
    expect(config.matcher).toContain(
      "/((?!api(?:/|$)|_next/|favicon.ico|site.webmanifest).*)",
    );
  });
});

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

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [sessionUrl, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(String(sessionUrl)).toBe("http://localhost/api/auth/session");
    expect(init.cache).toBe("no-store");
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
