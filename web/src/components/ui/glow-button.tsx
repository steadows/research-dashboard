import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary";

interface GlowButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: React.ReactNode;
}

/**
 * GlowButton — HUD-style button with glow effects.
 * Primary: solid cyan, black text. Secondary: ghost, cyan border, cyan text.
 * 0px border-radius, glow (not shadow).
 */
export function GlowButton({
  variant = "primary",
  children,
  className,
  ...props
}: GlowButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 px-5 py-2.5 font-headline text-sm uppercase tracking-wider transition-all active:scale-95",
        variant === "primary" && [
          "bg-accent-cyan text-bg-base",
          "hover:shadow-[0_0_20px_rgba(0,240,255,0.4)]",
        ],
        variant === "secondary" && [
          "border border-outline text-accent-cyan",
          "hover:border-transparent hover:bg-accent-cyan/10",
        ],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
