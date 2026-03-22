import { HUDBracket } from "@/components/effects/HUDBracket";
import { cn } from "@/lib/utils";

interface ContentPanelProps {
  children: React.ReactNode;
  /** Label displayed at the top-left of the HUD bracket frame */
  label?: string;
  /** Status text displayed at the top-right */
  status?: string;
  /** Additional classes for the outer wrapper */
  className?: string;
}

/**
 * ContentPanel — Main content area wrapper with HUD bracket frame.
 * Used as the primary container for page content sections.
 */
export function ContentPanel({
  children,
  label,
  status,
  className,
}: ContentPanelProps) {
  return (
    <HUDBracket
      label={label}
      status={status}
      accentColor="cyan"
      animated
      className={cn("bg-bg-surface/50", className)}
    >
      {children}
    </HUDBracket>
  );
}
