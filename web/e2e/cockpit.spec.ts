import { test, expect } from "@playwright/test";
import { CockpitPage } from "./pages/CockpitPage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Cockpit", () => {
  let cockpit: CockpitPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    cockpit = new CockpitPage(page);
    await cockpit.goto();
  });

  test("page loads with sidebar and empty state", async () => {
    await cockpit.expectSidebarVisible();
    await cockpit.expectEmptyState();
  });

  test("sidebar shows project list from API", async () => {
    // Mock projects should appear in sidebar
    await expect(
      cockpit.sidebar.locator("text=Research Dashboard")
    ).toBeVisible();
    await expect(cockpit.sidebar.locator("text=ML Pipeline")).toBeVisible();
  });

  test("selecting a project shows project content", async () => {
    await cockpit.selectProject("Research Dashboard");
    await cockpit.expectProjectSelected("Research Dashboard");
    await cockpit.expectStatsVisible();
  });

  test("stats panels show data after project selection", async ({ page }) => {
    await cockpit.selectProject("Research Dashboard");
    // LINKED_ITEMS should show count from mock data
    await expect(page.locator("text=LINKED_ITEMS")).toBeVisible();
    // GRAPH_NODES should show count
    await expect(page.locator("text=GRAPH_NODES")).toBeVisible();
  });

  test("search filter narrows project list", async () => {
    await cockpit.filterProjects("ML");
    await expect(cockpit.sidebar.locator("text=ML Pipeline")).toBeVisible();
    // Research Dashboard should be hidden
    await expect(
      cockpit.sidebar.locator("button").filter({ hasText: "Research Dashboard" })
    ).not.toBeVisible();
  });

  test("search with no results shows NO_RESULTS", async () => {
    await cockpit.filterProjects("nonexistent");
    await expect(cockpit.sidebar.locator("text=NO_RESULTS")).toBeVisible();
  });

  test("switching between projects updates content", async () => {
    await cockpit.selectProject("Research Dashboard");
    await cockpit.expectProjectSelected("Research Dashboard");

    await cockpit.selectProject("ML Pipeline");
    await cockpit.expectProjectSelected("ML Pipeline");
  });

  test("sidebar shows project count in footer", async ({ page }) => {
    await expect(page.locator("text=2 PROJECTS")).toBeVisible();
  });
});
