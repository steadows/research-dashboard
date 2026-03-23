import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Archive page (/archive).
 * Encapsulates filter interactions, card assertions, and restore actions.
 */
export class ArchivePage {
  readonly page: Page;
  readonly heading: Locator;
  readonly itemCount: Locator;
  readonly filterBar: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.locator("h2").filter({ hasText: /Archive/i });
    this.itemCount = page.locator("text=/\\d+ ITEMS/");
    this.filterBar = page.locator("button").filter({ hasText: "ALL" });
  }

  /** Navigate to archive page */
  async goto(): Promise<void> {
    await this.page.goto("/archive");
    await this.page.waitForLoadState("networkidle");
  }

  /** Assert the page loaded with heading */
  async expectPageLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  /** Assert the subtitle description is visible */
  async expectSubtitle(): Promise<void> {
    await expect(
      this.page.locator("text=DISMISSED ITEMS")
    ).toBeVisible();
  }

  /** Get all archived item cards */
  getArchivedCards(): Locator {
    return this.page.locator('[class*="border-l-4"][class*="bg-bg-surface"]');
  }

  /** Select a filter type button */
  async selectFilter(type: string): Promise<void> {
    await this.page
      .locator("button")
      .filter({ hasText: new RegExp(`^${type}$`, "i") })
      .click();
  }

  /** Assert item count display */
  async expectItemCount(count: number): Promise<void> {
    await expect(
      this.page.locator(`text=${count} ITEMS`)
    ).toBeVisible();
  }
}
