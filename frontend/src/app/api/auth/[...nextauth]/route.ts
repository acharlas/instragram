import type { NextAuthOptions } from "next-auth";
import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

type TokenResponse = {
  access_token: string;
  refresh_token: string;
};

type BackendProfile = {
  id: string;
  username: string;
  avatar_key?: string | null;
};

export type AuthorizedUser = {
  id: string;
  username: string;
  avatarUrl: string | null;
  accessToken: string;
  refreshToken: string;
};

const API_BASE_URL = process.env.BACKEND_API_URL ?? "http://backend:8000";

function buildApiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
}

export async function loginWithCredentials(username: string, password: string) {
  const response = await fetch(buildApiUrl("/api/v1/auth/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Invalid credentials");
  }

  const payload = (await response.json()) as TokenResponse;
  if (!payload.access_token || !payload.refresh_token) {
    throw new Error("Missing authentication tokens");
  }

  return payload;
}

export async function fetchUserProfile(accessToken: string) {
  const response = await fetch(buildApiUrl("/api/v1/me"), {
    headers: {
      Cookie: `access_token=${accessToken}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to load profile");
  }

  return (await response.json()) as BackendProfile;
}

export type CredentialsInput = {
  username?: string | null;
  password?: string | null;
};

type AuthorizationDependencies = {
  login: typeof loginWithCredentials;
  profile: typeof fetchUserProfile;
};

export async function authorizeWithCredentials(
  credentials: CredentialsInput,
  deps?: Partial<AuthorizationDependencies>,
): Promise<AuthorizedUser | null> {
  if (!credentials?.username || !credentials?.password) {
    return null;
  }

  const { login = loginWithCredentials, profile = fetchUserProfile } =
    deps ?? {};

  try {
    const tokens = await login(credentials.username, credentials.password);
    const profileData = await profile(tokens.access_token);

    return {
      id: profileData.id,
      username: profileData.username,
      avatarUrl: profileData.avatar_key ?? null,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    };
  } catch {
    return null;
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        return authorizeWithCredentials(credentials);
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        const authorizedUser = user as AuthorizedUser;
        token.userId = authorizedUser.id;
        token.username = authorizedUser.username;
        token.avatarUrl = authorizedUser.avatarUrl;
        token.accessToken = authorizedUser.accessToken;
        token.refreshToken = authorizedUser.refreshToken;
      }

      return token;
    },
    async session({ session, token }) {
      session.user = {
        id: token.userId as string,
        username: token.username as string,
        avatarUrl: (token.avatarUrl as string | null) ?? null,
      };
      session.accessToken = token.accessToken as string | undefined;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
