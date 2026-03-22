import { test, expect } from "@playwright/test";
import { AgenticHubPage } from "./pages/AgenticHubPage";
import { mockAllApiRoutes, MOCK_SUMMARY } from "./helpers/mock-api";

test.describe("Agentic Hub", () => {
  let hub: AgenticHubPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    hub = new AgenticHubPage(page);
    await hub.goto();
  });

  test("hub tab loads with heading and refresh button", async () => {
    await hub.expectLoaded();
    await hub.expectRefreshButton();
  });

  test("intel cards render from mock data", async () => {
    const cards = hub.getIntelCards();
    await expect(cards).toHaveCount(2);
  });

  test("first card shows post title and account", async ({ page }) => {
    await expect(page.locator("text=GPT-5 Architecture Deep Dive")).toBeVisible();
    await expect(page.locator("text=ai_research")).toBeVisible();
  });

  test("second card shows RLHF post", async ({ page }) => {
    await expect(page.locator("text=RLHF Alternatives")).toBeVisible();
    await expect(page.locator("text=ml_daily")).toBeVisible();
  });

  test("summarize button triggers API call and shows summary", async ({
    page,
  }) => {
    // The first card (analyzed) should show VIEW SUMMARY
    // The second card should show SUMMARIZE
    const secondCard = hub.getIntelCards().nth(1);
    const summarizeBtn = secondCard
      .locator("button")
      .filter({ hasText: /SUMMARIZE/i });

    await summarizeBtn.click();
    // After API response, should show the summary text
    await expect(
      page.locator(`text=${MOCK_SUMMARY.summary.slice(0, 30)}`)
    ).toBeVisible({ timeout: 5000 });
  });

  test("workbench button sends item and shows SENT", async ({ page }) => {
    const firstCard = hub.getIntelCards().first();
    const wbButton = firstCard
      .locator("button")
      .filter({ hasText: /WORKBENCH/i });

    await wbButton.click();
    // Should transition to SENT state
    await expect(
      firstCard.locator("button").filter({ hasText: "SENT" })
    ).toBeVisible({ timeout: 5000 });
  });

  test("refresh button is disabled when ALL filter is active", async () => {
    // By default, "ALL" filter is active — refresh should be disabled
    await expect(hub.refreshButton).toBeDisabled();
  });

  test("signal analysis sidebar renders with stats", async () => {
    await hub.expectSignalSidebar();
  });

  test("key points display on cards", async ({ page }) => {
    await expect(page.locator("text=Novel attention mechanism")).toBeVisible();
    await expect(page.locator("text=Sparse MoE routing")).toBeVisible();
  });

  test("tags render on cards", async ({ page }) => {
    // Tags should be uppercased
    await expect(page.locator("text=GPT")).toBeVisible();
    await expect(page.locator("text=ARCHITECTURE")).toBeVisible();
  });
});
