import type { NextAuthOptions } from "next-auth";
import * as nextAuth from "next-auth";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import * as authModule from "../../app/api/auth/[...nextauth]/route";
import { getSessionServer } from "../../lib/auth/session";

type CredentialsProvider = {
  id: string;
  authorize: (
    credentials: Record<string, unknown> | undefined,
    req: unknown,
  ) => Promise<authModule.AuthorizedUser | null>;
};

let authOptions: NextAuthOptions;
let credentialsProvider: CredentialsProvider;

beforeAll(() => {
  process.env.BACKEND_API_URL = "http://backend:8000";
  process.env.NEXTAUTH_SECRET = "test-secret";
  authOptions = authModule.authOptions;
  credentialsProvider = authOptions.providers.find(
    (provider): provider is CredentialsProvider => provider.id === "credentials",
  ) as CredentialsProvider;
  if (!credentialsProvider) {
    throw new Error("Credentials provider not found");
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("authorizeWithCredentials", () => {
  it("returns user details when backend login and profile succeed", async () => {
    const login = vi
      .fn()
      .mockResolvedValue({ access_token: "access-token", refresh_token: "refresh-token" });
    const profile = vi
      .fn()
      .mockResolvedValue({ id: "user-id", username: "string", avatar_key: "avatar-key" });

    const result = await authModule.authorizeWithCredentials(
      { username: "string", password: "stringst" },
      { login, profile },
    );

    expect(result).toEqual({
      id: "user-id",
      username: "string",
      avatarUrl: "avatar-key",
      accessToken: "access-token",
      refreshToken: "refresh-token",
    });
    expect(login).toHaveBeenCalledWith("string", "stringst");
    expect(profile).toHaveBeenCalledWith("access-token");
  });

  it("returns null when backend login fails", async () => {
    const login = vi.fn().mockRejectedValue(new Error("Invalid credentials"));
    const profile = vi.fn();

    const result = await authModule.authorizeWithCredentials(
      { username: "string", password: "wrong" },
      { login, profile },
    );

    expect(result).toBeNull();
    expect(login).toHaveBeenCalledWith("string", "wrong");
    expect(profile).not.toHaveBeenCalled();
  });

  it("returns null when profile retrieval fails", async () => {
    const login = vi
      .fn()
      .mockResolvedValue({ access_token: "access-token", refresh_token: "refresh-token" });
    const profile = vi.fn().mockRejectedValue(new Error("Unexpected failure"));

    const result = await authModule.authorizeWithCredentials(
      { username: "string", password: "stringst" },
      { login, profile },
    );

    expect(result).toBeNull();
    expect(login).toHaveBeenCalledWith("string", "stringst");
    expect(profile).toHaveBeenCalledWith("access-token");
  });

  it("returns null when credentials are missing", async () => {
    const login = vi.fn();
    const profile = vi.fn();

    const result = await authModule.authorizeWithCredentials(
      { username: "string", password: "" },
      { login, profile },
    );

    expect(result).toBeNull();
    expect(login).not.toHaveBeenCalled();
    expect(profile).not.toHaveBeenCalled();
  });
});

describe("HTTP helper functions", () => {
  it("loginWithCredentials returns tokens on 200 response", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "access-token",
        refresh_token: "refresh-token",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await authModule.loginWithCredentials("string", "stringst");

    expect(result).toEqual({
      access_token: "access-token",
      refresh_token: "refresh-token",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "string", password: "stringst" }),
      }),
    );
  });

  it("loginWithCredentials throws when response not ok", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(authModule.loginWithCredentials("string", "wrong")).rejects.toThrow(
      "Invalid credentials",
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("loginWithCredentials throws when tokens are missing", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "only-access",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(authModule.loginWithCredentials("string", "stringst")).rejects.toThrow(
      "Missing authentication tokens",
    );
  });

  it("fetchUserProfile returns data on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "user-id",
        username: "string",
        avatar_key: "avatar-key",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const profile = await authModule.fetchUserProfile("access-token");

    expect(profile).toEqual({
      id: "user-id",
      username: "string",
      avatar_key: "avatar-key",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/me",
      expect.objectContaining({
        headers: expect.objectContaining({
          Cookie: "access_token=access-token",
        }),
      }),
    );
  });

  it("fetchUserProfile throws when response not ok", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(authModule.fetchUserProfile("access-token")).rejects.toThrow(
      "Failed to load profile",
    );
  });
});

describe("getSessionServer", () => {
  it("delegates to next-auth getServerSession with authOptions", async () => {
    const session = { user: { id: "user-id" } } as unknown;
    const getter = vi.fn().mockResolvedValue(session);

    const result = await getSessionServer(getter as unknown as typeof nextAuth.getServerSession);

    expect(getter).toHaveBeenCalledWith(authModule.authOptions);
    expect(result).toBe(session);
  });
});

describe("JWT and session callbacks", () => {
  it("embeds tokens in JWT and keeps refresh server-side", async () => {
    const user: authModule.AuthorizedUser = {
      id: "user-id",
      username: "string",
      avatarUrl: "avatar-key",
      accessToken: "access-token",
      refreshToken: "refresh-token",
    };

    const jwt = await authOptions.callbacks?.jwt?.({
      token: {},
      user,
      account: null,
      profile: null,
      session: null,
      trigger: "signIn",
    });

    expect(jwt).toMatchObject({
      userId: "user-id",
      username: "string",
      avatarUrl: "avatar-key",
      accessToken: "access-token",
      refreshToken: "refresh-token",
    });

    const session = await authOptions.callbacks?.session?.({
      session: { user: { id: "", username: "", avatarUrl: null } },
      token: jwt ?? {},
      user: user as unknown as Record<string, unknown>,
    });

    expect(session).toMatchObject({
      user: {
        id: "user-id",
        username: "string",
        avatarUrl: "avatar-key",
      },
      accessToken: "access-token",
    });
    expect((session as Record<string, unknown>).refreshToken).toBeUndefined();
  });
});
