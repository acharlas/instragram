import type { ReactNode } from "react";

import { NavBar } from "@/components/ui/navbar";
import { getSessionServer } from "@/lib/auth/session";

export default async function ProtectedLayout({
  children,
}: {
  children: ReactNode;
}) {
  const session = await getSessionServer();
  const username = session?.user?.username ?? session?.user?.name ?? "";

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <NavBar username={username} />
      <main className="flex-1 overflow-y-auto bg-zinc-900 p-8">{children}</main>
    </div>
  );
}
