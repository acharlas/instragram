import { describe, expect, it } from "vitest";

import { SessionProvider as ExportedSessionProvider } from "../../app/providers";
import { SessionProvider as NextAuthSessionProvider } from "next-auth/react";

describe("app providers", () => {
  it("re-exports NextAuth SessionProvider", () => {
    expect(ExportedSessionProvider).toBe(NextAuthSessionProvider);
  });
});
