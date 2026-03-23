import { test, expect } from "@playwright/test";
import { ReportsPage } from "./pages/ReportsPage";
import { mockAllApiRoutes } from "./helpers/mock-api";

test.describe("Reports", () => {
  let reports: ReportsPage;

  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
    reports = new ReportsPage(page);
    await reports.goto();
  });

  test("page loads with title and subtitle", async () => {
    await reports.expectPageLoaded();
    await reports.expectSubtitle();
  });

  test("report count badge shows total", async () => {
    await reports.expectReportCount(2);
  });

  test("report cards render from mock data", async ({ page }) => {
    await expect(
      page.locator("text=TF-IDF Vectorizer Research")
    ).toBeVisible();
    await expect(
      page.locator("text=Attention Mechanism Deep Dive")
    ).toBeVisible();
  });

  test("report cards show source type badges", async ({ page }) => {
    // Source type badges should render
    await expect(page.locator("text=tool").first()).toBeVisible();
    await expect(page.locator("text=method").first()).toBeVisible();
  });

  test("report card shows excerpt text", async ({ page }) => {
    await expect(
      page.locator("text=Text vectorization utility for NLP pipelines.")
    ).toBeVisible();
  });

  test("first report shows HTML badge", async ({ page }) => {
    // The first report has has_html: true
    await expect(page.locator("text=HTML").first()).toBeVisible();
  });

  test("selecting a report opens content viewer", async ({ page }) => {
    await reports.selectReport("TF-IDF Vectorizer Research");
    await reports.expectContentViewer();
    // Content should include the markdown heading
    await expect(
      page.locator("text=TF-IDF Vectorizer Research").first()
    ).toBeVisible();
  });

  test("content viewer shows OPEN IN NEW TAB button", async () => {
    await reports.selectReport("TF-IDF Vectorizer Research");
    await reports.expectContentViewer();
  });

  test("clicking same report again deselects it", async ({ page }) => {
    await reports.selectReport("TF-IDF Vectorizer Research");
    await reports.expectContentViewer();
    // Click again to deselect
    await reports.selectReport("TF-IDF Vectorizer Research");
    // Content viewer should disappear
    await expect(
      page.locator("text=OPEN IN NEW TAB")
    ).not.toBeVisible({ timeout: 3000 });
  });
});
