import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Reports page (/reports).
 * Encapsulates report list, selection, and content viewer interactions.
 */
export class ReportsPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly reportCount: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator("h1").filter({ hasText: /Reports/i });
    this.reportCount = page.locator("text=/\\d+ REPORTS/");
  }

  /** Navigate to reports page */
  async goto(): Promise<void> {
    await this.page.goto("/reports");
    await this.page.waitForLoadState("networkidle");
  }

  /** Assert the page loaded with heading */
  async expectPageLoaded(): Promise<void> {
    await expect(this.pageTitle).toBeVisible();
  }

  /** Assert the subtitle text is visible */
  async expectSubtitle(): Promise<void> {
    await expect(
      this.page.locator("text=Generated Research Reports")
    ).toBeVisible();
  }

  /** Get all report card buttons */
  getReportCards(): Locator {
    return this.page.locator("button").filter({
      has: this.page.locator("h3"),
    });
  }

  /** Select a report by clicking its card */
  async selectReport(title: string): Promise<void> {
    await this.page
      .locator("button")
      .filter({ hasText: new RegExp(title, "i") })
      .click();
  }

  /** Assert the content viewer panel is visible */
  async expectContentViewer(): Promise<void> {
    await expect(
      this.page.locator("text=OPEN IN NEW TAB")
    ).toBeVisible({ timeout: 5000 });
  }

  /** Assert report count is shown */
  async expectReportCount(count: number): Promise<void> {
    await expect(
      this.page.locator(`text=${count} REPORTS`)
    ).toBeVisible();
  }
}
