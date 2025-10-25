"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type CommentFormProps = {
  postId: number;
};

export function CommentForm({ postId }: CommentFormProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const submit = (formData: FormData) => {
    const text = formData.get("comment")?.toString() ?? "";
    if (!text.trim()) {
      setError("Le commentaire est vide.");
      return;
    }

    startTransition(async () => {
      setError(null);
      try {
        const response = await fetch(`/api/posts/${postId}/comments`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text }),
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error("Request failed");
        }
        setValue("");
        router.refresh();
      } catch (err) {
        console.error("Failed to post comment", err);
        setError("Impossible d'envoyer le commentaire.");
      }
    });
  };

  return (
    <form
      className="mt-3 flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        submit(new FormData(event.currentTarget));
      }}
    >
      <input
        type="text"
        name="comment"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Écrire un commentaire…"
        className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-600"
        disabled={isPending}
        autoComplete="off"
      />
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
      <button
        type="submit"
        disabled={isPending}
        className="self-end rounded-lg bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-900 transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        Publier
      </button>
    </form>
  );
}
