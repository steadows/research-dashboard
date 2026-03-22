import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Agentic Hub — accessible via Dashboard tab.
 * Encapsulates refresh, summarize, and workbench interactions.
 */
export class AgenticHubPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly refreshButton: Locator;
  readonly filterBar: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.locator("h2").filter({ hasText: /AGENTIC HUB/i });
    this.refreshButton = page.locator("button").filter({ hasText: /REFRESH FEED/i });
    this.filterBar = page.locator("button").filter({ hasText: "ALL" });
  }

  /** Navigate to dashboard and switch to Agentic Hub tab */
  async goto(): Promise<void> {
    await this.page.goto("/");
    await this.page.waitForLoadState("networkidle");
    await this.page.locator('[data-tab="agentic-hub"]').click();
    // Wait for lazy-loaded tab content
    await expect(this.heading).toBeVisible({ timeout: 10_000 });
  }

  /** Assert the hub heading is visible */
  async expectLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  /** Assert refresh button exists */
  async expectRefreshButton(): Promise<void> {
    await expect(this.refreshButton).toBeVisible();
  }

  /** Get all intel cards */
  getIntelCards(): Locator {
    return this.page.locator('[class*="border-l-4"][class*="border-indigo"]');
  }

  /** Get the summarize button on a specific card */
  getSummarizeButton(cardIndex: number): Locator {
    return this.getIntelCards()
      .nth(cardIndex)
      .locator("button")
      .filter({ hasText: /SUMMARIZE|VIEW SUMMARY/i });
  }

  /** Get the workbench button on a specific card */
  getWorkbenchButton(cardIndex: number): Locator {
    return this.getIntelCards()
      .nth(cardIndex)
      .locator("button")
      .filter({ hasText: /WORKBENCH|SENT|SENDING/i });
  }

  /** Click summarize on the first card */
  async clickSummarize(cardIndex: number = 0): Promise<void> {
    await this.getSummarizeButton(cardIndex).click();
  }

  /** Click workbench on a card */
  async clickWorkbench(cardIndex: number = 0): Promise<void> {
    await this.getWorkbenchButton(cardIndex).click();
  }

  /** Select an account filter */
  async selectFilter(account: string): Promise<void> {
    await this.page
      .locator("button")
      .filter({ hasText: account })
      .click();
  }

  /** Assert the signal analysis sidebar is visible */
  async expectSignalSidebar(): Promise<void> {
    await expect(
      this.page.locator("text=SIGNAL ANALYSIS")
    ).toBeVisible();
  }
}
