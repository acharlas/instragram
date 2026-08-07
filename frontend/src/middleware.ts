import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { JWT } from "next-auth/jwt";
import { getToken } from "next-auth/jwt";

import {
  resolveSessionTokenState,
  type SessionTokenState,
} from "@/lib/auth/access-token";

const AUTH_PAGES = new Set(["/login", "/register"]);
const PUBLIC_FILE_PATHS = new Set(["/favicon.ico", "/site.webmanifest"]);
type SessionToken = Awaited<ReturnType<typeof getToken>>;

function normalizePathname(pathname: string) {
  if (pathname === "/") {
    return pathname;
  }
  return pathname.replace(/\/+$/u, "") || "/";
}

function isPublicAsset(pathname: string) {
  return pathname.startsWith("/_next/") || PUBLIC_FILE_PATHS.has(pathname);
}

async function readSessionToken(request: NextRequest) {
  try {
    return await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
  } catch (error) {
    console.warn("Failed to read session token", error);
    return null;
  }
}

function asJwtToken(token: SessionToken): JWT | null {
  if (!token || typeof token === "string") {
    return null;
  }
  return token;
}

function getSessionState(token: SessionToken): SessionTokenState {
  const jwtToken = asJwtToken(token);
  if (!jwtToken) {
    return "invalid";
  }
  return resolveSessionTokenState(jwtToken);
}

function buildLoginRedirect(request: NextRequest) {
  const redirectUrl = new URL("/login", request.url);
  const from = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  if (from && from !== "/") {
    redirectUrl.searchParams.set("from", from);
  }
  return redirectUrl;
}

async function syncSessionCookie(request: NextRequest, response: NextResponse) {
  try {
    const sessionResponse = await fetch(
      new URL("/api/auth/session", request.url),
      {
        headers: { cookie: request.headers.get("cookie") ?? "" },
        cache: "no-store",
      },
    );
    for (const cookie of sessionResponse.headers.getSetCookie()) {
      response.headers.append("set-cookie", cookie);
    }
  } catch {
    // ponytail: transient failure — next navigation retries; never block the page.
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const normalizedPath = normalizePathname(pathname);

  if (isPublicAsset(pathname)) {
    return NextResponse.next();
  }

  if (AUTH_PAGES.has(normalizedPath)) {
    const token = await readSessionToken(request);
    if (getSessionState(token) === "usable") {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  const token = await readSessionToken(request);
  const sessionState = getSessionState(token);
  if (sessionState === "invalid") {
    return NextResponse.redirect(buildLoginRedirect(request));
  }

  const response = NextResponse.next();
  if (sessionState === "recoverable") {
    // Rotation must run through next-auth's HTTP route: the RSC path
    // (getServerSession) discards Set-Cookie, so in-memory rotation leaves
    // the browser holding a revoked refresh token and the session dies.
    await syncSessionCookie(request, response);
  }
  return response;
}

export const config = {
  matcher: ["/((?!api(?:/|$)|_next/|favicon.ico|site.webmanifest).*)"],
};
