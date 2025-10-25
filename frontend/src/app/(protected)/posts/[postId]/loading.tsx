export default function PostDetailLoading() {
  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6 py-8 md:h-[80vh] md:flex-row md:items-stretch md:gap-0 animate-pulse">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 md:flex-1 md:rounded-r-none md:border-r-0">
        <div className="aspect-square w-full rounded-2xl bg-zinc-800 md:h-full md:rounded-r-none md:rounded-l-2xl" />
      </div>

      <div className="flex max-h-full flex-col rounded-2xl border border-zinc-800 bg-zinc-900 p-4 md:w-96 md:flex-none md:rounded-l-none md:border-l-0">
        <div className="mb-4 h-6 rounded bg-zinc-800" />
        <div className="mb-4 h-4 rounded bg-zinc-800" />
        <div className="flex-1 space-y-3 overflow-hidden pr-1">
          <div className="h-4 rounded bg-zinc-800" />
          <div className="h-4 rounded bg-zinc-800" />
          <div className="h-4 rounded bg-zinc-800" />
        </div>
        <div className="mt-4 h-8 rounded bg-zinc-800" />
      </div>
    </section>
  );
}
