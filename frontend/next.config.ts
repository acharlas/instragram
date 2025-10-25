import type { NextConfig } from "next";

const nextConfig: NextConfig = (() => {
  const base =
    process.env.NEXT_PUBLIC_MINIO_BASE_URL ??
    "http://localhost:9000/instagram-media";
  let images: NextConfig["images"] | undefined;

  try {
    const url = new URL(base);
    images = {
      remotePatterns: [
        {
          protocol: url.protocol.replace(/:$/u, ""),
          hostname: url.hostname,
          port: url.port || undefined,
          pathname: `${url.pathname.replace(/\/$/u, "")}/**`,
        },
      ],
    };
  } catch {
    images = undefined;
  }

  return {
    images,
  } satisfies NextConfig;
})();

export default nextConfig;
