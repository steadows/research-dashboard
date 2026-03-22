import { test, expect } from "@playwright/test";
import { DashboardPage } from "./pages/DashboardPage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Dashboard", () => {
  let dashboard: DashboardPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    dashboard = new DashboardPage(page);
    await dashboard.goto();
  });

  test("page loads with header nav and R.I.D. branding", async () => {
    await dashboard.expectHeaderNav();
  });

  test("all 7 dashboard tabs render with correct labels", async () => {
    await dashboard.expectAllTabsVisible();
    await dashboard.expectTabLabels();
  });

  test("Home tab is active by default", async () => {
    await dashboard.expectActiveTab("home");
  });

  test("clicking Blog Queue tab navigates to blog queue content", async ({
    page,
  }) => {
    await dashboard.selectTab("blog-queue");
    await dashboard.expectActiveTab("blog-queue");
    // Blog queue content should appear (lazy loaded)
    await expect(page.locator("text=Building a Research Dashboard")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("clicking Tools Radar tab shows tools content", async ({ page }) => {
    await dashboard.selectTab("tools-radar");
    await dashboard.expectActiveTab("tools-radar");
    await expect(page.locator("text=Cursor AI")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("clicking Research Archive tab loads archive content", async ({
    page,
  }) => {
    await dashboard.selectTab("research-archive");
    await dashboard.expectActiveTab("research-archive");
    // Wait for lazy load
    await page.waitForTimeout(2000);
    // Archive tab should be loaded (content depends on mock data)
    await expect(dashboard.getTab("research-archive")).toHaveClass(
      /text-accent-cyan/
    );
  });

  test("clicking AI Signal tab loads signal content", async () => {
    await dashboard.selectTab("ai-signal");
    await dashboard.expectActiveTab("ai-signal");
  });

  test("clicking Graph Insights tab loads graph content", async () => {
    await dashboard.selectTab("graph-insights");
    await dashboard.expectActiveTab("graph-insights");
  });

  test("clicking Agentic Hub tab loads hub content", async ({ page }) => {
    await dashboard.selectTab("agentic-hub");
    await dashboard.expectActiveTab("agentic-hub");
    await expect(page.locator("h2").filter({ hasText: /AGENTIC HUB/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("tab navigation cycles through all tabs", async () => {
    const tabs = [
      "blog-queue",
      "tools-radar",
      "research-archive",
      "ai-signal",
      "graph-insights",
      "agentic-hub",
      "home",
    ] as const;

    for (const tab of tabs) {
      await dashboard.selectTab(tab);
      await dashboard.expectActiveTab(tab);
    }
  });

  test("header nav links point to correct routes", async ({ page }) => {
    const header = page.locator("header");
    await expect(header.locator('a[href="/"]')).toHaveText("DASHBOARD");
    await expect(header.locator('a[href="/cockpit"]')).toHaveText("COCKPIT");
    await expect(header.locator('a[href="/workbench"]')).toHaveText("WORKBENCH");
    await expect(header.locator('a[href="/agentic-hub"]')).toHaveText(
      "AGENTIC HUB"
    );
  });
});
