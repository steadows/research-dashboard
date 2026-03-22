import { cn } from "@/lib/utils";

type StatusType = "online" | "offline" | "warning" | "error";

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  className?: string;
}

const statusConfig: Record<StatusType, { dotClass: string; textClass: string; defaultLabel: string }> = {
  online: {
    dotClass: "bg-accent-green shadow-[0_0_5px_#39ff14]",
    textClass: "text-accent-green",
    defaultLabel: "ONLINE",
  },
  offline: {
    dotClass: "bg-outline",
    textClass: "text-outline",
    defaultLabel: "OFFLINE",
  },
  warning: {
    dotClass: "bg-accent-amber shadow-[0_0_5px_#ffbf00]",
    textClass: "text-accent-amber",
    defaultLabel: "WARNING",
  },
  error: {
    dotClass: "bg-accent-red shadow-[0_0_5px_#ff003c]",
    textClass: "text-accent-red",
    defaultLabel: "ERROR",
  },
};

/**
 * StatusBadge — Inline status indicator with glowing dot and label.
 */
export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className={cn("inline-block h-1.5 w-1.5 rounded-full", config.dotClass)} />
      <span className={cn("font-headline text-[9px] uppercase tracking-[0.2em]", config.textClass)}>
        {label ?? config.defaultLabel}
      </span>
    </span>
  );
}
