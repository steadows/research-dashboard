import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Workbench page (/workbench).
 * Encapsulates kanban column assertions and card interactions.
 */
export class WorkbenchPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly kanbanBoard: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator("h1").filter({ hasText: /Workbench/i });
    this.kanbanBoard = page.locator('[class*="grid"]').filter({
      has: page.locator("section"),
    });
  }

  /** Navigate to workbench */
  async goto(): Promise<void> {
    await this.page.goto("/workbench");
    await this.page.waitForLoadState("networkidle");
  }

  /** Assert page title is visible */
  async expectPageLoaded(): Promise<void> {
    await expect(this.pageTitle).toBeVisible();
  }

  /** Get a kanban column by status label */
  getColumn(status: "QUEUED" | "RESEARCHING" | "COMPLETED"): Locator {
    return this.page.locator("section").filter({
      has: this.page.locator(`h2:has-text("${status}")`),
    });
  }

  /** Assert all three kanban columns are visible */
  async expectAllColumnsVisible(): Promise<void> {
    await expect(this.getColumn("QUEUED")).toBeVisible();
    await expect(this.getColumn("RESEARCHING")).toBeVisible();
    await expect(this.getColumn("COMPLETED")).toBeVisible();
  }

  /** Assert a column has a specific count badge */
  async expectColumnCount(
    status: "QUEUED" | "RESEARCHING" | "COMPLETED",
    count: number
  ): Promise<void> {
    const countText = String(count).padStart(2, "0");
    await expect(
      this.getColumn(status).locator(`text=COUNT: ${countText}`)
    ).toBeVisible();
  }

  /** Assert a card with given name exists in a column */
  async expectCardInColumn(
    status: "QUEUED" | "RESEARCHING" | "COMPLETED",
    cardName: string
  ): Promise<void> {
    await expect(
      this.getColumn(status).locator(`text=${cardName}`)
    ).toBeVisible();
  }

  /** Get the pipeline subtitle text */
  getSubtitle(): Locator {
    return this.page.locator("text=Mission Control Research Pipeline");
  }
}
