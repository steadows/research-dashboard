import type { Locator, Page } from "@playwright/test";
import { expect } from "@playwright/test";

/** Dashboard tab identifiers matching DashboardTab type */
const TAB_IDS = [
  "home",
  "blog-queue",
  "tools-radar",
  "research-archive",
  "ai-signal",
  "graph-insights",
  "agentic-hub",
] as const;

const TAB_LABELS = [
  "HOME",
  "BLOG QUEUE",
  "TOOLS RADAR",
  "RESEARCH ARCHIVE",
  "AI SIGNAL",
  "GRAPH INSIGHTS",
  "AGENTIC HUB",
] as const;

type TabId = (typeof TAB_IDS)[number];

/**
 * Page Object Model for the Dashboard page (/).
 * Encapsulates tab navigation, header nav, and content assertions.
 */
export class DashboardPage {
  readonly page: Page;
  readonly header: Locator;
  readonly tabBar: Locator;

  constructor(page: Page) {
    this.page = page;
    this.header = page.locator("header");
    this.tabBar = page.locator("[data-tab]").first().locator("..");
  }

  /** Navigate to the dashboard */
  async goto(): Promise<void> {
    await this.page.goto("/");
    await this.page.waitForLoadState("networkidle");
  }

  /** Get a tab button by its data-tab attribute */
  getTab(id: TabId): Locator {
    return this.page.locator(`[data-tab="${id}"]`);
  }

  /** Click a dashboard tab */
  async selectTab(id: TabId): Promise<void> {
    await this.getTab(id).click();
  }

  /** Assert that all 7 tabs are visible in the tab bar */
  async expectAllTabsVisible(): Promise<void> {
    for (const id of TAB_IDS) {
      await expect(this.getTab(id)).toBeVisible();
    }
  }

  /** Assert tab labels match expected text */
  async expectTabLabels(): Promise<void> {
    for (let i = 0; i < TAB_IDS.length; i++) {
      await expect(this.getTab(TAB_IDS[i])).toHaveText(TAB_LABELS[i]);
    }
  }

  /** Assert the active tab has cyan styling (text color class) */
  async expectActiveTab(id: TabId): Promise<void> {
    await expect(this.getTab(id)).toHaveClass(/text-accent-cyan/);
  }

  /** Assert header nav links exist */
  async expectHeaderNav(): Promise<void> {
    await expect(this.header).toBeVisible();
    await expect(this.header.locator("text=R.I.D.")).toBeVisible();
    await expect(this.header.locator('a[href="/"]')).toBeVisible();
    await expect(this.header.locator('a[href="/cockpit"]')).toBeVisible();
    await expect(this.header.locator('a[href="/workbench"]')).toBeVisible();
    await expect(this.header.locator('a[href="/agentic-hub"]')).toBeVisible();
  }
}
