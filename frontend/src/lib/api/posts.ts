import { apiServerFetch } from "./client";

export type PostDetail = {
  id: number;
  author_id: string;
  author_name: string | null;
  image_key: string;
  caption: string | null;
  like_count: number;
  viewer_has_liked: boolean;
};

export type PostComment = {
  id: number;
  author_id: string;
  author_name: string | null;
  author_username: string | null;
  text: string;
  created_at: string;
};

export type CreatedComment = PostComment;

export async function fetchPostDetail(
  postId: string,
  accessToken?: string,
): Promise<PostDetail | null> {
  if (!accessToken) {
    return null;
  }

  try {
    return await apiServerFetch<PostDetail>(`/api/v1/posts/${postId}`, {
      cache: "no-store",
      headers: {
        Cookie: `access_token=${accessToken}`,
      },
    });
  } catch (error) {
    console.error("Failed to load post detail", error);
    return null;
  }
}

export async function fetchPostComments(
  postId: string,
  accessToken?: string,
): Promise<PostComment[]> {
  if (!accessToken) {
    return [];
  }

  try {
    return await apiServerFetch<PostComment[]>(
      `/api/v1/posts/${postId}/comments`,
      {
        cache: "no-store",
        headers: {
          Cookie: `access_token=${accessToken}`,
        },
      },
    );
  } catch (error) {
    console.error("Failed to load post comments", error);
    return [];
  }
}

type LikeMutationResponse = {
  detail: string;
  like_count?: number;
};

export async function likePostRequest(
  postId: string,
  accessToken?: string,
): Promise<number | null> {
  if (!accessToken) {
    accessToken = undefined;
  }

  try {
    const payload = await apiServerFetch<LikeMutationResponse>(
      `/api/v1/posts/${postId}/likes`,
      {
        method: "POST",
        cache: "no-store",
        headers: accessToken
          ? {
              Cookie: `access_token=${accessToken}`,
            }
          : undefined,
      },
    );
    return typeof payload.like_count === "number" ? payload.like_count : null;
  } catch (error) {
    console.error("Failed to like post", error);
    return null;
  }
}

export async function unlikePostRequest(
  postId: string,
  accessToken?: string,
): Promise<number | null> {
  if (!accessToken) {
    accessToken = undefined;
  }

  try {
    const payload = await apiServerFetch<LikeMutationResponse>(
      `/api/v1/posts/${postId}/likes`,
      {
        method: "DELETE",
        cache: "no-store",
        headers: accessToken
          ? {
              Cookie: `access_token=${accessToken}`,
            }
          : undefined,
      },
    );
    return typeof payload.like_count === "number" ? payload.like_count : null;
  } catch (error) {
    console.error("Failed to unlike post", error);
    return null;
  }
}

export async function createPostComment(
  postId: string,
  text: string,
  accessToken?: string,
): Promise<CreatedComment | null> {
  if (!accessToken) {
    accessToken = undefined;
  }

  try {
    return await apiServerFetch<CreatedComment>(
      `/api/v1/posts/${postId}/comments`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken
            ? {
                Cookie: `access_token=${accessToken}`,
              }
            : {}),
        },
        body: JSON.stringify({ text }),
      },
    );
  } catch (error) {
    console.error("Failed to create comment", error);
    return null;
  }
}
