import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiServerFetch } from "../../lib/api/client";

const originalFetch = globalThis.fetch;

vi.mock("next/headers", () => ({
  cookies: () =>
    Promise.resolve({
      getAll: () => [
        { name: "next-auth.session-token", value: "session123" },
        { name: "custom", value: "value" },
      ],
    }),
}));

describe("apiServerFetch", () => {
  beforeEach(() => {
    process.env.BACKEND_API_URL = "http://backend:8000";
  });

  afterEach(() => {
    if (originalFetch) {
      globalThis.fetch = originalFetch;
    }
    vi.restoreAllMocks();
  });

  it("merges cookies when calling backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ hello: "world" }),
    });
    globalThis.fetch = fetchMock as unknown as typeof globalThis.fetch;

    await apiServerFetch("/api/test", {
      headers: {
        Cookie: "access_token=session-token",
      },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/test",
      expect.objectContaining({
        headers: expect.objectContaining({
          Cookie:
            "access_token=session-token; next-auth.session-token=session123; custom=value",
        }),
      }),
    );
  });
});
