import type { Mock } from "vitest";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api/client", () => ({
  apiServerFetch: vi.fn(),
}));

import { apiServerFetch } from "../../lib/api/client";
import {
  fetchPostComments,
  fetchPostDetail,
  createPostComment,
  likePostRequest,
  unlikePostRequest,
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
      like_count: 3,
      viewer_has_liked: true,
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
    expect(result?.like_count).toBe(3);
    expect(result?.viewer_has_liked).toBe(true);
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

describe("likePostRequest", () => {
  it("sends POST to like endpoint", async () => {
    apiServerFetchMock.mockResolvedValueOnce({ detail: "Liked", like_count: 5 });
    const result = await likePostRequest("42", "token123");
    expect(result).toBe(5);
    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/posts/42/likes",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Cookie: "access_token=token123",
        }),
      }),
    );
  });

  it("returns null on failure", async () => {
    apiServerFetchMock.mockRejectedValueOnce(new Error("nope"));
    const result = await likePostRequest("42", "token123");
    expect(result).toBeNull();
  });
});

describe("unlikePostRequest", () => {
  it("sends DELETE to unlike endpoint", async () => {
    apiServerFetchMock.mockResolvedValueOnce({ detail: "Unliked", like_count: 4 });
    const result = await unlikePostRequest("42", "token123");
    expect(result).toBe(4);
    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/posts/42/likes",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Cookie: "access_token=token123",
        }),
      }),
    );
  });

  it("returns null on failure", async () => {
    apiServerFetchMock.mockRejectedValueOnce(new Error("bad"));
    const result = await unlikePostRequest("42", "token123");
    expect(result).toBeNull();
  });
});

describe("createPostComment", () => {
  it("posts comment payload", async () => {
    const mockComment = {
      id: 1,
      post_id: 42,
      author_id: "user-1",
      author_name: "User One",
      author_username: "user1",
      text: "Hello",
      created_at: "2024-01-01T00:00:00Z",
    };
    apiServerFetchMock.mockResolvedValueOnce(mockComment);

    const result = await createPostComment("42", "Hello", "token123");
    expect(result).toEqual(mockComment);
    expect(apiServerFetchMock).toHaveBeenCalledWith(
      "/api/v1/posts/42/comments",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Cookie: "access_token=token123",
        }),
        body: JSON.stringify({ text: "Hello" }),
      }),
    );
  });

  it("returns null on failure", async () => {
    apiServerFetchMock.mockRejectedValueOnce(new Error("nope"));
    const result = await createPostComment("42", "Hello", "token123");
    expect(result).toBeNull();
  });
});
