import Image from "next/image";
import { CommentForm } from "@/components/post/CommentForm";
import { LikeButton } from "@/components/post/LikeButton";
import { fetchPostComments, fetchPostDetail } from "@/lib/api/posts";
import { getSessionServer } from "@/lib/auth/session";
import { buildImageUrl } from "@/lib/image";
import { sanitizeHtml } from "@/lib/sanitize";

type PostPageProps = { params: Promise<{ postId: string }> };

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

export default async function PostDetailPage({ params }: PostPageProps) {
  const { postId } = await params;
  const session = await getSessionServer();
  const accessToken = session?.accessToken as string | undefined;

  const [post, comments] = await Promise.all([
    fetchPostDetail(postId, accessToken),
    fetchPostComments(postId, accessToken),
  ]);

  if (!post) {
    return (
      <section className="mx-auto flex w-full max-w-xl flex-col gap-4 py-8 text-center text-sm text-zinc-500">
        <p>Ce contenu est introuvable.</p>
      </section>
    );
  }

  const authorLabel = post.author_name ?? post.author_id;
  const imageUrl = buildImageUrl(post.image_key);
  const safeCaption = post.caption ? sanitizeHtml(post.caption) : "";

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6 py-8 md:h-[80vh] md:flex-row md:items-stretch md:gap-0">
      <article className="rounded-2xl border border-zinc-800 bg-zinc-900 md:flex-1 md:rounded-r-none md:border-r-0">
        <div className="relative aspect-square w-full overflow-hidden rounded-2xl bg-zinc-800 md:h-full md:rounded-r-none md:rounded-l-2xl">
          <Image
            src={imageUrl}
            alt={`Publication ${post.id}`}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 600px"
            unoptimized
          />
        </div>
      </article>

      <aside
        id="comments"
        className="flex max-h-full flex-col rounded-2xl border border-zinc-800 bg-zinc-900 p-4 md:w-96 md:flex-none md:rounded-l-none md:border-l-0"
      >
        <header className="mb-4 border-b border-zinc-800 pb-3">
          <p className="text-sm font-semibold text-zinc-100">{authorLabel}</p>
          <p className="mt-2 text-sm text-zinc-200">
            {safeCaption || "Aucune légende"}
          </p>
        </header>

        <div className="flex-1 overflow-y-auto pr-1">
          {comments.length === 0 ? (
            <p className="text-sm text-zinc-500">Pas encore de commentaires.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {comments.map((comment) => (
                <li key={comment.id} className="text-sm text-zinc-200">
                  <span className="font-semibold text-zinc-100">
                    {comment.author_username ?? comment.author_name ?? comment.author_id}
                  </span>
                  : {comment.text}
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="mt-4 border-t border-zinc-800 pt-4">
          <div className="flex items-center gap-3 text-zinc-300">
            <LikeButton
              postId={post.id}
              initialLiked={post.viewer_has_liked}
              initialCount={post.like_count}
            />
            <span className="rounded-full p-2 text-zinc-400">
              <CommentIcon />
            </span>
          </div>
          <CommentForm postId={post.id} />
        </footer>
      </aside>
    </section>
  );
}
