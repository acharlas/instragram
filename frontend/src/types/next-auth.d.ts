import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      username: string;
      avatarUrl: string | null;
    };
    accessToken?: string;
  }

  interface User {
    id: string;
    username: string;
    avatarUrl: string | null;
    accessToken: string;
    refreshToken: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId?: string;
    username?: string;
    avatarUrl?: string | null;
    accessToken?: string;
    refreshToken?: string;
  }
}
