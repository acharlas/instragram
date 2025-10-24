"use client";

import { useSession } from "next-auth/react";

export function useAuth() {
  return useSession();
}
