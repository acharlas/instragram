import { describe, expect, it } from "vitest";

import {
  clearAuthCookies,
  getAccessTokenCookie,
  getRefreshTokenCookie,
  setAccessTokenCookie,
  setRefreshTokenCookie,
} from "../../lib/auth/cookies";

type StoredCookie = {
  value: string;
  options: Record<string, unknown>;
};

function createStore() {
  const store = new Map<string, StoredCookie>();
  return {
    set(name: string, value: string, options: Record<string, unknown>) {
      store.set(name, { value, options });
    },
    get(name: string) {
      const entry = store.get(name);
      return entry ? { value: entry.value } : undefined;
    },
    delete(name: string) {
      store.delete(name);
    },
    inspect(name: string) {
      return store.get(name);
    },
  };
}

describe("auth cookies helpers", () => {
  it("writes secure httpOnly options for access token", () => {
    const store = createStore();

    setAccessTokenCookie("access", 60, store);

    const cookie = store.inspect("access_token");
    expect(cookie).toBeDefined();
    expect(cookie?.value).toBe("access");
    expect(cookie?.options).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      secure: true,
      path: "/",
      maxAge: 60,
    });
  });

  it("writes secure httpOnly options for refresh token", () => {
    const store = createStore();

    setRefreshTokenCookie("refresh", 120, store);

    const cookie = store.inspect("refresh_token");
    expect(cookie?.value).toBe("refresh");
    expect(cookie?.options).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      secure: true,
      path: "/",
      maxAge: 120,
    });
  });

  it("reads cookies when present and returns null otherwise", () => {
    const store = createStore();
    setAccessTokenCookie("access", 60, store);

    expect(getAccessTokenCookie(store)).toBe("access");
    expect(getRefreshTokenCookie(store)).toBeNull();
  });

  it("clears both cookies", () => {
    const store = createStore();
    setAccessTokenCookie("access", 60, store);
    setRefreshTokenCookie("refresh", 60, store);

    clearAuthCookies(store);

    expect(store.inspect("access_token")).toBeUndefined();
    expect(store.inspect("refresh_token")).toBeUndefined();
  });
});
