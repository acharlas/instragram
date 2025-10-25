import { describe, expect, it } from "vitest";

import { buildImageUrl } from "../../lib/image";

describe("buildImageUrl", () => {
  it("concatenates base url and key", () => {
    process.env.NEXT_PUBLIC_MINIO_BASE_URL =
      "http://localhost:9000/instagram-media/";
    expect(buildImageUrl("posts/id/photo.jpg")).toBe(
      "http://localhost:9000/instagram-media/posts/id/photo.jpg",
    );
  });
});
