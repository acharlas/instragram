const DEFAULT_BASE_URL =
  process.env.NEXT_PUBLIC_MINIO_BASE_URL ??
  "http://localhost:9000/instagram-media";

export function buildImageUrl(objectKey: string): string {
  const trimmedBase = DEFAULT_BASE_URL.replace(/\/+$/u, "");
  const trimmedKey = objectKey.replace(/^\/+/, "");
  return `${trimmedBase}/${trimmedKey}`;
}
