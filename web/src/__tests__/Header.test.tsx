import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// next/navigation must be mocked before importing the component
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

// next/link renders an <a> tag in test environments
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// GlitchText is a pure text wrapper — mock to avoid animation complexity
vi.mock("@/components/effects/GlitchText", () => ({
  GlitchText: ({
    children,
    as: Tag = "span",
    ...props
  }: {
    children: React.ReactNode;
    as?: keyof React.JSX.IntrinsicElements;
    [key: string]: unknown;
  }) => <Tag {...props}>{children}</Tag>,
}));

import { usePathname } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { NAV_ROUTES } from "@/lib/navigation";

describe("Header", () => {
  it("renders the R.I.D. brand text", () => {
    render(<Header />);
    expect(screen.getByText("R.I.D.")).toBeInTheDocument();
  });

  it("renders all primary navigation links", () => {
    render(<Header />);
    for (const { label } of NAV_ROUTES) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("renders nav links with correct hrefs", () => {
    render(<Header />);
    for (const { href, label } of NAV_ROUTES) {
      const link = screen.getByText(label).closest("a");
      expect(link).toHaveAttribute("href", href);
    }
  });

  it("marks the active route with aria-current=page", () => {
    vi.mocked(usePathname).mockReturnValue("/cockpit");
    render(<Header />);
    const activeLink = screen.getByText("COCKPIT").closest("a");
    expect(activeLink).toHaveAttribute("aria-current", "page");
  });

  it("does not mark inactive routes with aria-current", () => {
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Header />);
    const inactiveLink = screen.getByText("WORKBENCH").closest("a");
    expect(inactiveLink).not.toHaveAttribute("aria-current");
  });

  it("renders a main navigation landmark", () => {
    render(<Header />);
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("renders Notifications action button", () => {
    render(<Header />);
    expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  });

  it("renders Settings action button", () => {
    render(<Header />);
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
  });

  it("renders a header element as the root", () => {
    render(<Header />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });
});
