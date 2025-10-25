"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
  icon: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/search", label: "Search", icon: "🔍" },
  { href: "/explore", label: "Explore", icon: "🧭" },
  { href: "/posts/new", label: "Create", icon: "➕" },
  { href: "/profile", label: "Profile", icon: "👤" },
];

type NavBarProps = {
  username?: string;
};

export function NavBar({ username }: NavBarProps) {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-56 flex-col border-r border-zinc-800 bg-zinc-950 p-6 text-zinc-100">
      <div className="mb-8 text-2xl font-semibold">Instragram</div>

      <nav className="flex-1 space-y-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-zinc-800 font-semibold"
                  : "text-zinc-300 hover:bg-zinc-900"
              }`}
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <footer className="mt-auto flex items-center gap-3 text-sm text-zinc-300">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-700 text-lg">
          ☺
        </div>
        <span>{username ?? "invité"}</span>
      </footer>
    </aside>
  );
}
