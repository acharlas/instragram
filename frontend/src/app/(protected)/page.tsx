import Image from "next/image";

import { apiServerFetch } from "@/lib/api/client";
import { getSessionServer } from "@/lib/auth/session";
import { buildImageUrl } from "@/lib/image";
import { sanitizeHtml } from "@/lib/sanitize";
import type { FeedPost } from "@/types/feed";

async function getHomeFeed(accessToken?: string): Promise<FeedPost[]> {
  if (!accessToken) {
    return [];
  }

  try {
    return await apiServerFetch<FeedPost[]>("/api/v1/feed/home", {
      cache: "no-store",
      headers: {
        Cookie: `access_token=${accessToken}`,
      },
    });
  } catch (error) {
    console.error("Failed to load feed", error);
    return [];
  }
}

function PostCard({ post }: { post: FeedPost }) {
  const safeCaption = post.caption ? sanitizeHtml(post.caption) : "";
  const imageUrl = buildImageUrl(post.image_key);
  const displayName = post.author_name ?? post.author_id;
  const initials = displayName
    .split(/\s+/u)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
      <header className="mb-3 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
          {initials || displayName.slice(0, 2).toUpperCase()}
        </div>
        <div className="text-sm">
          <p className="font-semibold text-zinc-100">{displayName}</p>
        </div>
      </header>

      <div className="relative mb-3 aspect-square w-full overflow-hidden rounded-xl bg-zinc-800">
        <Image
          src={imageUrl}
          alt={`Publication ${post.id}`}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 600px"
          unoptimized
        />
      </div>

      {safeCaption ? (
        <p className="text-sm text-zinc-200">{safeCaption}</p>
      ) : (
        <p className="text-sm text-zinc-500">Aucune légende</p>
      )}
    </article>
  );
}

export default async function ProtectedHomePage() {
  const session = await getSessionServer();
  const accessToken = session?.accessToken as string | undefined;
  const posts = await getHomeFeed(accessToken);

  return (
    <section className="mx-auto flex w-full max-w-2xl flex-col gap-6 py-8">
      {posts.length === 0 ? (
        <p className="text-center text-sm text-zinc-500">
          Le fil d&apos;actualité est vide pour le moment.
        </p>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
    </section>
  );
}
