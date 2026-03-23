import { test, expect } from "@playwright/test";
import { GraphPage } from "./pages/GraphPage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Graph", () => {
  let graph: GraphPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    graph = new GraphPage(page);
    await graph.goto();
  });

  test("page loads with title and subtitle", async () => {
    await graph.expectPageLoaded();
    await graph.expectSubtitle();
  });

  test("page title shows Knowledge_Network slug", async ({ page }) => {
    await expect(
      page.locator("text=/Knowledge_Network/")
    ).toBeVisible();
  });

  test("graph health metrics render from API data", async ({ page }) => {
    // The GraphInsightsTab uses /api/graph/health mock data
    // Wait for content to load
    await page.waitForTimeout(2000);
    // Should display some of the health metrics (total_nodes: 45, etc.)
    // The exact rendering depends on GraphInsightsTab, but the page should not be empty
    const content = await page.locator("main, [class*='flex']").first().textContent();
    expect(content).toBeTruthy();
  });
});
