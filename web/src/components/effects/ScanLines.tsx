"use client";

export function ScanLines() {
  return (
    <div className="pointer-events-none fixed inset-0 z-50" aria-hidden="true">
      {/* Static CRT scan lines */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 1px, rgba(0, 240, 255, 0.08) 1px, rgba(0, 240, 255, 0.08) 2px)",
          backgroundSize: "100% 4px",
        }}
      />
      {/* Animated sweep line */}
      <div className="absolute inset-x-0 h-[2px] motion-safe:animate-scan-line bg-gradient-to-r from-transparent via-accent-cyan/20 to-transparent" />
    </div>
  );
}
