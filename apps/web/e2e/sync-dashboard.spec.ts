import { expect, test, type Page } from "@playwright/test";

async function syncTickerAndAssertNoPlaceholders(page: Page, ticker: string, expectedCompanyHeading: string) {
  const tickerInput = page.getByLabel("Ticker symbol");
  const syncButton = page.getByRole("button", { name: "Sync ticker" });

  await tickerInput.fill(ticker);
  await expect(syncButton).toHaveCSS("cursor", "pointer");
  await syncButton.click();

  await expect(page.getByTestId("active-ticker")).toContainText(ticker.toUpperCase());
  await expect(page.getByText(expectedCompanyHeading)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Revenue vs. Net Income" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Free Cash Flow" })).toBeVisible();
  await expect(page.getByText(/^Pending$/)).toHaveCount(0);

  const filingHistory = page.getByTestId("filing-history");
  await expect(filingHistory).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Year" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Filing" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Valuation" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Shareholder Returns" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Quality / Risk" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Pricing Power" })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "OE-DCF", exact: true })).toBeVisible();
  await expect(filingHistory.getByRole("columnheader", { name: "Revenue YoY" })).toBeVisible();
  await expect(
    filingHistory.getByText(/Market data required|SEC fact unavailable|Dividend data unavailable|Not applicable/),
  ).toHaveCount(0);

  const glossary = page.getByTestId("metric-glossary");
  await expect(glossary).toBeVisible();
  await expect(glossary.getByText("Meaning and formulas")).toBeVisible();
  await expect(glossary.getByText("Formula: PE / CAGR_percent_points")).toBeVisible();
}

test("syncing AAPL and COST renders zero-placeholder yearly tables", async ({ page }) => {
  const observedRequests: string[] = [];

  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/")) {
      observedRequests.push(`${request.method()} ${url}`);
    }
  });

  await page.goto("/");

  const tickerInput = page.getByLabel("Ticker symbol");

  await expect(tickerInput).toHaveValue("AAPL");
  await expect(page.getByTestId("active-ticker")).toContainText("AAPL");

  await syncTickerAndAssertNoPlaceholders(page, "AAPL", "Apple Inc. filings");

  await syncTickerAndAssertNoPlaceholders(page, "cost", "COSTCO WHOLESALE CORP /NEW filings");

  await page.screenshot({
    path: "../../output/playwright/sync-dashboard-cost.png",
    fullPage: true,
  });

  expect(observedRequests.some((request) => request.includes("/api/v1/sync/AAPL"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/status/AAPL"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/financials/AAPL"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/sync/COST"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/status/COST"))).toBe(true);
  expect(observedRequests.some((request) => request.includes("/api/v1/financials/COST"))).toBe(true);
});
