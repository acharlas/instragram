import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const PUBLIC_PATHS = new Set(["/login", "/register"]);
const AUTH_COOKIE_NAMES = [
  "next-auth.session-token",
  "__Secure-next-auth.session-token",
];

function isPublicPath(pathname: string) {
  return (
    PUBLIC_PATHS.has(pathname) ||
    pathname.startsWith("/api/auth") ||
    pathname.startsWith("/api/public")
  );
}

function hasSessionCookie(request: NextRequest): boolean {
  return AUTH_COOKIE_NAMES.some((name) =>
    Boolean(request.cookies.get(name)?.value),
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!hasSessionCookie(request)) {
    const redirectUrl = new URL("/login", request.url);
    redirectUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|site.webmanifest).*)"],
};
