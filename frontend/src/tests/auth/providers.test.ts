import { SessionProvider as NextAuthSessionProvider } from "next-auth/react";
import { describe, expect, it } from "vitest";

import { SessionProvider as ExportedSessionProvider } from "../../app/providers";

describe("app providers", () => {
  it("re-exports NextAuth SessionProvider", () => {
    expect(ExportedSessionProvider).toBe(NextAuthSessionProvider);
  });
});
