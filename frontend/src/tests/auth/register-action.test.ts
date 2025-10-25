import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { registerUser } from "../../app/(public)/register/page";

describe("registerUser", () => {
  const ORIGINAL_ENV = process.env.BACKEND_API_URL;

  beforeEach(() => {
    process.env.BACKEND_API_URL = "http://backend:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    process.env.BACKEND_API_URL = ORIGINAL_ENV;
  });

  it("returns success when the API accepts the registration", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    const formData = new FormData();
    formData.set("username", "alice");
    formData.set("email", "alice@example.com");
    formData.set("password", "Sup3rSecret!");

    const result = await registerUser(formData);

    expect(result).toEqual({ success: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("returns error when API responds with detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "User exists" }),
      }),
    );

    const formData = new FormData();
    formData.set("username", "alice");
    formData.set("email", "alice@example.com");
    formData.set("password", "Sup3rSecret!");

    const result = await registerUser(formData);

    expect(result).toEqual({ success: false, error: "User exists" });
  });

  it("validates inputs before calling API", async () => {
    const formData = new FormData();
    formData.set("username", "al");
    formData.set("email", "aliceexample.com");
    formData.set("password", "short");

    const result = await registerUser(formData);

    expect(result).toEqual({
      success: false,
      error: "Le nom d'utilisateur doit contenir au moins 3 caractères",
    });
  });
});
