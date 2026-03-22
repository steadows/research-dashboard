"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface SidebarItem {
  href: string;
  icon: React.ReactNode;
  label: string;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  {
    href: "/archive",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
      </svg>
    ),
    label: "ARCHIVE",
  },
  {
    href: "/graph",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M3 20.25h18M3.75 3v16.5h16.5" />
      </svg>
    ),
    label: "GRAPH",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="fixed left-0 top-16 z-40 hidden h-[calc(100vh-64px)] w-20 flex-col items-center border-r border-accent-cyan/20 bg-bg-surface/80 py-8 backdrop-blur-xl md:flex"
        aria-label="Utility tools"
      >
        <div className="mb-6 flex flex-col items-center gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-accent-cyan/50">
            Tools
          </span>
        </div>

        <nav className="flex w-full flex-col items-center gap-6" aria-label="Utility navigation">
          {SIDEBAR_ITEMS.map(({ href, icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-label={label}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex w-full flex-col items-center gap-1 py-2 transition-all duration-75",
                  isActive
                    ? "border-l-2 border-accent-cyan bg-accent-cyan/10 text-accent-cyan"
                    : "text-slate-500 hover:text-accent-cyan"
                )}
              >
                {icon}
                <span className="font-mono text-[9px] uppercase">{label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Mobile bottom nav — sidebar items are secondary, shown as trailing icons */}
      {/* Primary mobile nav (page routes) is handled by Header's mobile menu */}
    </>
  );
}
