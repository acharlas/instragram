import { apiServerFetch } from "./client";

export type PostDetail = {
  id: number;
  author_id: string;
  author_name: string | null;
  image_key: string;
  caption: string | null;
};

export type PostComment = {
  id: number;
  author_id: string;
  author_name: string | null;
  text: string;
  created_at: string;
};

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
