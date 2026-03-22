import { test, expect } from "@playwright/test";
import { WorkbenchPage } from "./pages/WorkbenchPage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Workbench", () => {
  let workbench: WorkbenchPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    workbench = new WorkbenchPage(page);
    await workbench.goto();
  });

  test("page loads with title and subtitle", async () => {
    await workbench.expectPageLoaded();
    await expect(workbench.getSubtitle()).toBeVisible();
  });

  test("all three kanban columns render", async () => {
    await workbench.expectAllColumnsVisible();
  });

  test("columns show correct count badges", async () => {
    await workbench.expectColumnCount("QUEUED", 1);
    await workbench.expectColumnCount("RESEARCHING", 1);
    await workbench.expectColumnCount("COMPLETED", 1);
  });

  test("cards appear in correct columns", async () => {
    await workbench.expectCardInColumn("QUEUED", "TF-IDF Vectorizer");
    await workbench.expectCardInColumn("RESEARCHING", "Attention Mechanism");
    await workbench.expectCardInColumn("COMPLETED", "LangChain Framework");
  });

  test("queued card has start research action", async ({ page }) => {
    const queuedColumn = workbench.getColumn("QUEUED");
    // Should have a button to start research
    await expect(
      queuedColumn.locator("button").filter({ hasText: /START|RESEARCH/i })
    ).toBeVisible();
  });

  test("completed card has view report action", async ({ page }) => {
    const completedColumn = workbench.getColumn("COMPLETED");
    await expect(
      completedColumn.locator("button").filter({ hasText: /REPORT|VIEW/i })
    ).toBeVisible();
  });

  test("pipeline subtitle shows version", async ({ page }) => {
    await expect(page.locator("text=/Pipeline_v2.04/")).toBeVisible();
  });
});
