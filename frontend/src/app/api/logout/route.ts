import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

import { ApiError, apiServerFetch } from "@/lib/api/client";

type NextAuthTokenRequest = Parameters<typeof getToken>[0]["req"];

function buildAuthCookieHeader(
  accessToken?: string,
  refreshToken?: string,
): string | null {
  const parts: string[] = [];
  if (accessToken) {
    parts.push(`access_token=${accessToken}`);
  }
  if (refreshToken) {
    parts.push(`refresh_token=${refreshToken}`);
  }
  return parts.length > 0 ? parts.join("; ") : null;
}

export async function POST(request: Request) {
  const token = await getToken({
    req: request as NextAuthTokenRequest,
    secret: process.env.NEXTAUTH_SECRET,
  });
  const accessToken =
    typeof token?.accessToken === "string" ? token.accessToken : undefined;
  const refreshToken =
    typeof token?.refreshToken === "string" ? token.refreshToken : undefined;
  const authCookieHeader = buildAuthCookieHeader(accessToken, refreshToken);

  try {
    await apiServerFetch("/api/v1/auth/logout", {
      method: "POST",
      cache: "no-store",
      headers: authCookieHeader ? { Cookie: authCookieHeader } : undefined,
    });
    return NextResponse.json({ success: true, revoked: true });
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return NextResponse.json({ success: true, revoked: false });
      }
      return NextResponse.json(
        {
          success: false,
          revoked: false,
          detail: error.message ?? null,
        },
        { status: 502 },
      );
    }
    console.error("Unexpected error during logout", error);
    return NextResponse.json(
      {
        success: false,
        revoked: false,
        detail: "Unexpected error",
      },
      { status: 502 },
    );
  }
}
