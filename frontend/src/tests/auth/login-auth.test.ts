import { describe, expect, it, vi } from "vitest";

import { authenticateCredentials } from "../../app/(public)/login/_components/login-form";

describe("authenticateCredentials", () => {
  it("returns true when NextAuth succeeds", async () => {
    const authenticator = vi.fn().mockResolvedValue({ ok: true, error: null });

    const result = await authenticateCredentials(
      "alice",
      "password123",
      authenticator,
    );

    expect(result).toBe(true);
    expect(authenticator).toHaveBeenCalledWith("credentials", {
      username: "alice",
      password: "password123",
      redirect: false,
    });
  });

  it("returns false when authentication fails", async () => {
    const authenticator = vi
      .fn()
      .mockResolvedValue({ ok: false, error: "CredentialsSignin" });

    const result = await authenticateCredentials(
      "alice",
      "bad-pass",
      authenticator,
    );

    expect(result).toBe(false);
  });

  it("returns false when authenticator throws", async () => {
    const authenticator = vi.fn().mockRejectedValue(new Error("network"));

    await expect(
      authenticateCredentials("alice", "pass", authenticator),
    ).resolves.toBe(false);
  });
});
