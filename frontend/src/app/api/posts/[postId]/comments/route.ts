import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

import { createPostComment } from "@/lib/api/posts";

type RouteParams = {
  params: { postId: string };
};

export async function POST(request: Request, route: RouteParams) {
  const { postId } = route.params;
  const token = await getToken({ req: request });
  const accessToken = (token?.accessToken as string | undefined) ?? undefined;

  if (!accessToken) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );
  }

  const { text } = (await request.json().catch(() => ({}))) as {
    text?: string;
  };

  if (!text || !text.trim()) {
    return NextResponse.json(
      { detail: "Comment text is required" },
      { status: 400 },
    );
  }

  const comment = await createPostComment(postId, text, accessToken);
  if (!comment) {
    return NextResponse.json(
      { detail: "Unable to create comment" },
      { status: 500 },
    );
  }

  return NextResponse.json(comment, { status: 201 });
}
