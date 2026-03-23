import { test, expect } from "@playwright/test";
import { ArchivePage } from "./pages/ArchivePage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Archive", () => {
  let archive: ArchivePage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    archive = new ArchivePage(page);
    await archive.goto();
  });

  test("page loads with heading and subtitle", async () => {
    await archive.expectPageLoaded();
    await archive.expectSubtitle();
  });

  test("item count shows total archived items", async () => {
    await archive.expectItemCount(3);
  });

  test("archived cards render from mock data", async ({ page }) => {
    await expect(page.locator("text=Deprecated Lib")).toBeVisible();
    await expect(page.locator("text=Old Approach")).toBeVisible();
    await expect(page.locator("text=Stale IG Post")).toBeVisible();
  });

  test("cards show type badges", async ({ page }) => {
    await expect(page.locator("text=TOOL").first()).toBeVisible();
    await expect(page.locator("text=METHOD").first()).toBeVisible();
  });

  test("filter buttons render for available types", async ({ page }) => {
    // ALL filter should be present
    await expect(
      page.locator("button").filter({ hasText: /^ALL$/ })
    ).toBeVisible();
  });

  test("selecting type filter narrows displayed items", async ({ page }) => {
    // Click "tool" filter
    await archive.selectFilter("tool");
    // Should show only tool items
    await expect(page.locator("text=Deprecated Lib")).toBeVisible();
    // Method and instagram items should be hidden
    await expect(page.locator("text=Old Approach")).not.toBeVisible();
    await expect(page.locator("text=Stale IG Post")).not.toBeVisible();
  });

  test("ALL filter shows all items again", async ({ page }) => {
    await archive.selectFilter("tool");
    await expect(page.locator("text=Old Approach")).not.toBeVisible();
    // Switch back to ALL
    await archive.selectFilter("ALL");
    await expect(page.locator("text=Deprecated Lib")).toBeVisible();
    await expect(page.locator("text=Old Approach")).toBeVisible();
    await expect(page.locator("text=Stale IG Post")).toBeVisible();
  });
});
