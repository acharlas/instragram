import { cookies } from "next/headers";

type SameSite = "lax" | "strict" | "none";

type CookieOptions = {
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: SameSite;
  path?: string;
  maxAge?: number;
};

type CookieDescriptor = { value: string };

type CookieStore = {
  get(name: string): CookieDescriptor | undefined;
  set(name: string, value: string, options: CookieOptions): void;
  delete(name: string): void;
};

const ACCESS_COOKIE = "access_token";
const REFRESH_COOKIE = "refresh_token";
const COOKIE_PATH = "/";
const SAME_SITE: SameSite = "lax";
const SECURE_DEFAULT = process.env.NODE_ENV !== "development";

function resolveStore(store?: CookieStore): CookieStore {
  return store ?? (cookies() as unknown as CookieStore);
}

function buildOptions(maxAgeSeconds: number): CookieOptions {
  return {
    httpOnly: true,
    secure: SECURE_DEFAULT,
    sameSite: SAME_SITE,
    path: COOKIE_PATH,
    maxAge: maxAgeSeconds,
  };
}

export function setAccessTokenCookie(
  value: string,
  maxAgeSeconds: number,
  store?: CookieStore,
) {
  resolveStore(store).set(ACCESS_COOKIE, value, buildOptions(maxAgeSeconds));
}

export function setRefreshTokenCookie(
  value: string,
  maxAgeSeconds: number,
  store?: CookieStore,
) {
  resolveStore(store).set(REFRESH_COOKIE, value, buildOptions(maxAgeSeconds));
}

export function getAccessTokenCookie(store?: CookieStore): string | null {
  return resolveStore(store).get(ACCESS_COOKIE)?.value ?? null;
}

export function getRefreshTokenCookie(store?: CookieStore): string | null {
  return resolveStore(store).get(REFRESH_COOKIE)?.value ?? null;
}

export function clearAuthCookies(store?: CookieStore): void {
  const target = resolveStore(store);
  target.delete(ACCESS_COOKIE);
  target.delete(REFRESH_COOKIE);
}
