import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { GlowButton } from "@/components/ui/glow-button";

describe("GlowButton", () => {
  it("renders children text", () => {
    render(<GlowButton>CLICK ME</GlowButton>);
    expect(screen.getByRole("button", { name: "CLICK ME" })).toBeInTheDocument();
  });

  it("fires click handler", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<GlowButton onClick={onClick}>ACTION</GlowButton>);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire click when disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <GlowButton onClick={onClick} disabled>
        DISABLED
      </GlowButton>
    );
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("applies primary variant by default", () => {
    render(<GlowButton>Primary</GlowButton>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-accent-cyan");
  });

  it("applies secondary variant styles", () => {
    render(<GlowButton variant="secondary">Secondary</GlowButton>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("border");
    expect(btn.className).toContain("text-accent-cyan");
  });

  it("passes through HTML button attributes", () => {
    render(<GlowButton type="submit">Submit</GlowButton>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });
});
