import Image from "next/image";

import { fetchPostComments, fetchPostDetail } from "@/lib/api/posts";
import { getSessionServer } from "@/lib/auth/session";
import { buildImageUrl } from "@/lib/image";
import { sanitizeHtml } from "@/lib/sanitize";

type PostPageProps = { params: Promise<{ postId: string }> };

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
    <section className="mx-auto flex w-full max-w-xl flex-col gap-6 py-8">
      <article className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
        <header className="mb-4">
          <p className="text-sm font-semibold text-zinc-100">{authorLabel}</p>
        </header>

        <div className="relative mb-4 aspect-square w-full overflow-hidden rounded-xl bg-zinc-800">
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

      <section className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-100">
          Commentaires
        </h2>

        {comments.length === 0 ? (
          <p className="text-sm text-zinc-500">Pas encore de commentaires.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {comments.map((comment) => (
              <li key={comment.id} className="text-sm text-zinc-200">
                <span className="font-semibold text-zinc-100">
                  {comment.author_name ?? comment.author_id}
                </span>
                : {comment.text}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
