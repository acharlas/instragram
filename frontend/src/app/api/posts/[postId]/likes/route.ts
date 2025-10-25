import { NextResponse } from "next/server";

import {
  likePostRequest,
  unlikePostRequest,
} from "@/lib/api/posts";
import { getSessionServer } from "@/lib/auth/session";

type RouteParams = {
  params: { postId: string };
};

export async function POST(_: Request, route: RouteParams) {
  const { postId } = route.params;
  const session = await getSessionServer();
  const accessToken = session?.accessToken as string | undefined;

  if (!accessToken) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );
  }

  const likeCount = await likePostRequest(postId, accessToken);
  if (likeCount === null) {
    return NextResponse.json(
      { detail: "Unable to like post" },
      { status: 500 },
    );
  }
  return NextResponse.json(
    { detail: "Liked", like_count: likeCount },
    { status: 200 },
  );
}

export async function DELETE(_: Request, route: RouteParams) {
  const { postId } = route.params;
  const session = await getSessionServer();
  const accessToken = session?.accessToken as string | undefined;

  if (!accessToken) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );
  }

  const likeCount = await unlikePostRequest(postId, accessToken);
  if (likeCount === null) {
    return NextResponse.json(
      { detail: "Unable to unlike post" },
      { status: 500 },
    );
  }
  return NextResponse.json(
    { detail: "Unliked", like_count: likeCount },
    { status: 200 },
  );
}
