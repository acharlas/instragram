import { describe, expect, it, vi } from "vitest";

const getTokenMock = vi.hoisted(() => vi.fn());
const apiServerFetchMock = vi.hoisted(() => vi.fn());

vi.mock("next-auth/jwt", () => ({
  getToken: getTokenMock,
}));

vi.mock("@/lib/api/client", async () => {
  class MockApiError extends Error {
    readonly status: number;

    constructor(status: number, message?: string) {
      super(message ?? `API request failed with status ${status}`);
      this.name = "ApiError";
      this.status = status;
    }
  }

  return {
    ApiError: MockApiError,
    apiServerFetch: apiServerFetchMock,
  };
});

import { ApiError } from "@/lib/api/client";
import { POST } from "../../app/api/logout/route";

describe("POST /api/logout", () => {
  it("forwards access and refresh tokens to backend logout", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "access-token",
      refreshToken: "refresh-token",
    });
    apiServerFetchMock.mockResolvedValueOnce({});

    const response = await POST(new Request("http://localhost/api/logout"));
    const payload = (await response.json()) as {
      success?: boolean;
      revoked?: boolean;
    };

    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        headers: {
          Cookie: "access_token=access-token; refresh_token=refresh-token",
        },
      }),
    );
    expect(payload.success).toBe(true);
    expect(payload.revoked).toBe(true);
  });

  it("treats backend 401 as successful local logout", async () => {
    getTokenMock.mockResolvedValueOnce({
      accessToken: "expired-access",
      refreshToken: "expired-refresh",
    });
    apiServerFetchMock.mockRejectedValueOnce(new ApiError(401, "Unauthorized"));

    const response = await POST(new Request("http://localhost/api/logout"));
    const payload = (await response.json()) as {
      success?: boolean;
      revoked?: boolean;
    };

    expect(response.status).toBe(200);
    expect(payload.success).toBe(true);
    expect(payload.revoked).toBe(false);
  });

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
});
