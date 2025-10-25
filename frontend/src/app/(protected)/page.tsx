import Image from "next/image";
import Link from "next/link";

import { LikeButton } from "@/components/post/LikeButton";
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

function CommentIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 12a8.25 8.25 0 0 1-11.513 7.6L6.6 20.4l.8-2.887A8.25 8.25 0 1 1 21 12Z"
      />
    </svg>
  );
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
      <Link
        href={`/posts/${post.id}`}
        className="block space-y-3 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
      >
        <header className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
            {initials || displayName.slice(0, 2).toUpperCase()}
          </div>
          <div className="text-sm">
            <p className="font-semibold text-zinc-100">{displayName}</p>
          </div>
        </header>

        <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-zinc-800">
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
      </Link>

      <footer className="mt-4 flex items-center gap-3 text-zinc-300">
        <LikeButton
          postId={post.id}
          initialLiked={post.viewer_has_liked}
          initialCount={post.like_count}
        />
        <Link
          href={`/posts/${post.id}`}
          className="rounded-full p-2 transition hover:text-zinc-100"
          aria-label="Voir les commentaires"
        >
          <CommentIcon />
        </Link>
      </footer>
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
