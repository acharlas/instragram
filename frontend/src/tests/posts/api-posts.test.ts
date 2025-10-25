import type { Mock } from "vitest";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api/client", () => ({
  apiServerFetch: vi.fn(),
}));

import { apiServerFetch } from "../../lib/api/client";
import {
  fetchPostComments,
  fetchPostDetail,
} from "../../lib/api/posts";

const apiServerFetchMock = apiServerFetch as unknown as Mock;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchPostDetail", () => {
  it("returns null when no access token is provided", async () => {
    const result = await fetchPostDetail("42");
    expect(result).toBeNull();
    expect(apiServerFetchMock).not.toHaveBeenCalled();
  });

  it("fetches post detail with cookie header", async () => {
    apiServerFetchMock.mockResolvedValueOnce({
      id: 42,
      author_id: "user-1",
      author_name: "User One",
      caption: "Hello",
      image_key: "photos/hello.jpg",
    });

    const result = await fetchPostDetail("42", "token123");

    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/posts/42",
      expect.objectContaining({
        headers: expect.objectContaining({
          Cookie: "access_token=token123",
        }),
      }),
    );
    expect(result?.id).toBe(42);
  });

  it("returns null when request fails", async () => {
    apiServerFetchMock.mockRejectedValueOnce(new Error("boom"));

    const result = await fetchPostDetail("42", "token123");
    expect(result).toBeNull();
  });
});

describe("fetchPostComments", () => {
  it("returns empty array when no access token is provided", async () => {
    const result = await fetchPostComments("42");
    expect(result).toEqual([]);
    expect(apiServerFetchMock).not.toHaveBeenCalled();
  });

  it("fetches comments with cookie header", async () => {
    apiServerFetchMock.mockResolvedValueOnce([
      {
        id: 1,
        author_id: "user-1",
        author_name: "User One",
        text: "Nice shot!",
        created_at: "2024-01-01T00:00:00Z",
      },
    ]);

    const result = await fetchPostComments("42", "token123");

    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/posts/42/comments",
      expect.objectContaining({
        headers: expect.objectContaining({
          Cookie: "access_token=token123",
        }),
      }),
    );
    expect(result).toHaveLength(1);
  });

  it("returns empty array when request fails", async () => {
    apiServerFetchMock.mockRejectedValueOnce(new Error("boom"));

    const result = await fetchPostComments("42", "token123");
    expect(result).toEqual([]);
  });
});
