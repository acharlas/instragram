import { apiServerFetch } from "@/lib/api/client";
import { getSessionServer } from "@/lib/auth/session";
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

  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
      <header className="mb-3 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
          {post.author_id.slice(0, 2).toUpperCase()}
        </div>
        <div className="text-sm">
          <p className="font-semibold text-zinc-100">{post.author_id}</p>
          <p className="text-xs text-zinc-400">Post #{post.id}</p>
        </div>
      </header>

      <div className="mb-3 aspect-square w-full overflow-hidden rounded-xl bg-zinc-800">
        <div className="flex h-full items-center justify-center text-zinc-500">
          {post.image_key}
        </div>
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
  const posts = await getHomeFeed(session?.accessToken as string | undefined);

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
