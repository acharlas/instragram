import { describe, expect, it } from "vitest";
import { securityHeaders } from "../../../next.config";

describe("next config security headers", () => {
  it("sets nosniff", () => {
    expect(securityHeaders).toContainEqual({
      key: "X-Content-Type-Options",
      value: "nosniff",
    });
  });
  it("denies framing", () => {
    expect(securityHeaders).toContainEqual({
      key: "X-Frame-Options",
      value: "DENY",
    });
  });
  it("sets strict referrer policy", () => {
    expect(securityHeaders).toContainEqual({
      key: "Referrer-Policy",
      value: "strict-origin-when-cross-origin",
    });
  });
  it("disables intrusive permissions", () => {
    expect(securityHeaders).toContainEqual({
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=()",
    });
  });
  it("enables HSTS", () => {
    expect(securityHeaders).toContainEqual({
      key: "Strict-Transport-Security",
      value: "max-age=31536000; includeSubDomains",
    });
  });
});
