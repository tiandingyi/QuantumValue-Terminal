import { expect, test } from "@playwright/test";

test("syncing COST updates the dashboard and renders historical filing data", async ({ page }) => {
  const observedRequests: string[] = [];

  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/")) {
      observedRequests.push(`${request.method()} ${url}`);
    }
  });

  await page.goto("/");

  const tickerInput = page.getByLabel("Ticker symbol");
  const syncButton = page.getByRole("button", { name: "Sync ticker" });

  await expect(tickerInput).toHaveValue("AAPL");
  await expect(page.getByTestId("active-ticker")).toContainText("AAPL");

  await tickerInput.fill("cost");
  await expect(syncButton).toHaveCSS("cursor", "pointer");

  await syncButton.click();

  await expect(page.getByTestId("active-ticker")).toContainText("COST");
  await expect(page.getByText("COSTCO WHOLESALE CORP /NEW filings")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Revenue vs. Net Income" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Free Cash Flow" })).toBeVisible();
  await expect(page.getByText("Market data input required")).toHaveCount(0);
  await expect(page.getByText("Pending")).toHaveCount(0);

  const filingHistory = page.getByTestId("filing-history");
  await expect(filingHistory).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Period" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Revenue" })).toBeVisible();
  await expect(filingHistory.getByText("2026 Q1")).toBeVisible();
  await expect(filingHistory.getByText("2025 FY")).toBeVisible();

  await page.screenshot({
    path: "../../output/playwright/sync-dashboard-cost.png",
    fullPage: true,
  });

  expect(observedRequests.some((request) => request.includes("/api/v1/sync/COST"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/status/COST"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/financials/COST"))).toBe(true);
});
