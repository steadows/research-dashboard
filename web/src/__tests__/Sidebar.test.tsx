import { render, screen, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

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

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";

describe("Sidebar", () => {
  it("renders the desktop utility navigation landmark", () => {
    render(<Sidebar />);
    expect(
      screen.getByRole("navigation", { name: "Utility navigation" })
    ).toBeInTheDocument();
  });

  it("renders the mobile utility navigation landmark", () => {
    render(<Sidebar />);
    expect(
      screen.getByRole("navigation", { name: "Utility navigation (mobile)" })
    ).toBeInTheDocument();
  });

  it("renders the Tools section label", () => {
    render(<Sidebar />);
    expect(screen.getByText("Tools")).toBeInTheDocument();
  });

  it("renders ARCHIVE link in desktop nav", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    expect(within(desktopNav).getByRole("link", { name: "ARCHIVE" })).toBeInTheDocument();
  });

  it("renders GRAPH link in desktop nav", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    expect(within(desktopNav).getByRole("link", { name: "GRAPH" })).toBeInTheDocument();
  });

  it("renders REPORTS link in desktop nav", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    expect(within(desktopNav).getByRole("link", { name: "REPORTS" })).toBeInTheDocument();
  });

  it("renders ARCHIVE link with correct href", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    const link = within(desktopNav).getByRole("link", { name: "ARCHIVE" });
    expect(link).toHaveAttribute("href", "/archive");
  });

  it("renders GRAPH link with correct href", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    const link = within(desktopNav).getByRole("link", { name: "GRAPH" });
    expect(link).toHaveAttribute("href", "/graph");
  });

  it("renders REPORTS link with correct href", () => {
    render(<Sidebar />);
    const desktopNav = screen.getByRole("navigation", { name: "Utility navigation" });
    const link = within(desktopNav).getByRole("link", { name: "REPORTS" });
    expect(link).toHaveAttribute("href", "/reports");
  });

  it("marks active route with aria-current=page in both navs", () => {
    vi.mocked(usePathname).mockReturnValue("/archive");
    render(<Sidebar />);
    const archiveLinks = screen.getAllByRole("link", { name: "ARCHIVE" });
    expect(archiveLinks).toHaveLength(2);
    archiveLinks.forEach((link) => {
      expect(link).toHaveAttribute("aria-current", "page");
    });
  });

  it("does not mark inactive routes with aria-current", () => {
    vi.mocked(usePathname).mockReturnValue("/archive");
    render(<Sidebar />);
    const graphLinks = screen.getAllByRole("link", { name: "GRAPH" });
    graphLinks.forEach((link) => {
      expect(link).not.toHaveAttribute("aria-current");
    });
  });

  it("renders an aside element for desktop sidebar", () => {
    render(<Sidebar />);
    expect(
      screen.getByRole("complementary", { name: "Utility tools" })
    ).toBeInTheDocument();
  });

  it("renders mobile nav links with correct hrefs", () => {
    render(<Sidebar />);
    const mobileNav = screen.getByRole("navigation", { name: "Utility navigation (mobile)" });
    expect(within(mobileNav).getByRole("link", { name: "ARCHIVE" })).toHaveAttribute("href", "/archive");
    expect(within(mobileNav).getByRole("link", { name: "GRAPH" })).toHaveAttribute("href", "/graph");
    expect(within(mobileNav).getByRole("link", { name: "REPORTS" })).toHaveAttribute("href", "/reports");
  });
});
