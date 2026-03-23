import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Graph page (/graph).
 * Encapsulates graph health metrics and community detection UI.
 */
export class GraphPage {
  readonly page: Page;
  readonly pageTitle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator("h1").filter({ hasText: /Graph/i });
  }

  /** Navigate to graph page */
  async goto(): Promise<void> {
    await this.page.goto("/graph");
    await this.page.waitForLoadState("networkidle");
  }

  /** Assert the page loaded with heading */
  async expectPageLoaded(): Promise<void> {
    await expect(this.pageTitle).toBeVisible();
  }

  /** Assert the subtitle text is visible */
  async expectSubtitle(): Promise<void> {
    await expect(
      this.page.locator("text=Vault Graph Health")
    ).toBeVisible();
  }
}
