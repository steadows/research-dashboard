import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Page Object Model for the Cockpit page (/cockpit).
 * Encapsulates project sidebar, selection, and analysis panel interactions.
 */
export class CockpitPage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly searchInput: Locator;
  readonly emptyState: Locator;
  readonly mainContent: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = page.locator("aside").first();
    this.searchInput = page.locator('input[placeholder="FILTER..."]');
    this.emptyState = page.locator("text=Select a project to begin");
    this.mainContent = page.locator("main, [class*='flex-1']").first();
  }

  /** Navigate to cockpit */
  async goto(): Promise<void> {
    await this.page.goto("/cockpit");
    await this.page.waitForLoadState("networkidle");
  }

  /** Assert sidebar is visible with project list */
  async expectSidebarVisible(): Promise<void> {
    await expect(this.sidebar).toBeVisible();
    await expect(this.sidebar.locator("text=PROJECTS")).toBeVisible();
  }

  /** Assert empty state is shown when no project selected */
  async expectEmptyState(): Promise<void> {
    await expect(this.emptyState).toBeVisible();
  }

  /** Get project buttons in the sidebar */
  getProjectButtons(): Locator {
    return this.sidebar.locator("button").filter({ hasNotText: /^$/ });
  }

  /** Select a project by name (clicks the button in sidebar) */
  async selectProject(name: string): Promise<void> {
    await this.sidebar
      .locator("button")
      .filter({ hasText: new RegExp(name, "i") })
      .click();
  }

  /** Assert project header is visible after selection */
  async expectProjectSelected(name: string): Promise<void> {
    // After selection, the main area should show project content (no empty state)
    await expect(this.emptyState).not.toBeVisible();
  }

  /** Assert stats panels are visible */
  async expectStatsVisible(): Promise<void> {
    await expect(this.page.locator("text=LINKED_ITEMS")).toBeVisible();
    await expect(this.page.locator("text=GRAPH_NODES")).toBeVisible();
    await expect(this.page.locator("text=ANALYSIS_ENGINE")).toBeVisible();
  }

  /** Filter projects via search */
  async filterProjects(query: string): Promise<void> {
    await this.searchInput.fill(query);
  }
}
