import { cn } from "@/lib/utils";

type BadgeVariant = "journalclub" | "tldr" | "method" | "tool" | "instagram" | "default";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  journalclub: "border-accent-green text-accent-green bg-accent-green/10",
  tldr: "border-accent-amber text-accent-amber bg-accent-amber/10",
  method: "border-purple text-purple bg-purple/10",
  tool: "border-accent-green text-accent-green bg-accent-green/10",
  instagram: "border-indigo text-indigo bg-indigo/10",
  default: "border-outline text-outline bg-outline/10",
};

/**
 * Badge — Rectangular label badge with no rounded corners.
 * Matches design system: label-sm typography, 0px border-radius.
 */
export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-block border px-2 py-0.5 font-headline text-[10px] uppercase",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
