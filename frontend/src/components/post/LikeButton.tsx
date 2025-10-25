"use client";

import { useState, useTransition } from "react";

type LikeButtonProps = {
  postId: number;
  initialLiked?: boolean;
  initialCount?: number;
};

function HeartIcon({ filled }: { filled: boolean }) {
  const stroke = filled ? "currentColor" : "currentColor";
  const fill = filled ? "currentColor" : "none";
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill={fill}
      stroke={stroke}
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 3.75a4.5 4.5 0 0 1 3.182 7.697l-7.182 7.051-7.182-7.051a4.5 4.5 0 1 1 6.364-6.364l.818.817.818-.817A4.48 4.48 0 0 1 16.5 3.75Z"
      />
    </svg>
  );
}

export function LikeButton({
  postId,
  initialLiked = false,
  initialCount = 0,
}: LikeButtonProps) {
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [isPending, startTransition] = useTransition();

  const toggle = () => {
    if (isPending) {
      return;
    }
    const previousLiked = liked;
    const previousCount = count;
    const nextLiked = !liked;
    const method = nextLiked ? "POST" : "DELETE";
    startTransition(async () => {
      setLiked(nextLiked);
      setCount((prev) =>
        Math.max(0, prev + (nextLiked ? 1 : -1)),
      );
      try {
        const response = await fetch(`/api/posts/${postId}/likes`, {
          method,
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error("Request failed");
        }
        const data = (await response.json().catch(() => null)) as
          | { like_count?: number }
          | null;
        if (typeof data?.like_count === "number") {
          setCount(data.like_count);
        }
      } catch (error) {
        console.error("Failed to toggle like", error);
        setLiked(previousLiked);
        setCount(previousCount);
      }
    });
  };

  return (
    <div className="flex items-center gap-2 text-zinc-300">
      <button
        type="button"
        onClick={toggle}
        disabled={isPending}
        aria-pressed={liked}
        className="rounded-full p-2 transition hover:text-zinc-100 disabled:opacity-50"
        aria-label={liked ? "Retirer le like" : "Aimer la publication"}
      >
        <HeartIcon filled={liked} />
      </button>
      <span aria-live="polite" className="text-sm">
        {count}
      </span>
    </div>
  );
}
