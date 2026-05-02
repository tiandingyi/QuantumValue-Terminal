import assert from "node:assert/strict";
import test from "node:test";

import { metricCards, priceSeries } from "../lib/dashboard-data";
import {
  FinancialsResponse,
  buildDerivedGlossary,
  buildFilingRows,
  buildScorecard,
  buildTrendPoints,
  derivedColumnGroups,
  derivedTableColumns,
  hasIncompleteHistory,
  selectDisplayFilings,
} from "../lib/financials";

test("dashboard data includes metric cards and a matching price series", () => {
  assert.ok(metricCards.length >= 3);
  assert.equal(priceSeries.labels.length, priceSeries.values.length);
});

test("financials helpers build chart points and scorecard values", () => {
  const financials: FinancialsResponse = {
    ticker: "AAPL",
    cik: "0000320193",
    company: "Apple Inc.",
    status: "ready",
    updated_at: "2026-04-13T00:00:00Z",
    filings: [
      {
        form_type: "10-Q",
        period_end_date: "2027-03-31",
        filed_at: "2027-05-01",
        accession_number: "q",
        updated_at: "2027-05-02T00:00:00Z",
        base_metrics: {
          revenue: 800,
          net_income: 90,
        },
        derived_metrics: {
          free_cash_flow: { name: "Free Cash Flow", value: 80, unit: "USD", end: "2027-03-31", filed: null },
          oe_dcf_total: { status: "ready", value: 120, unit: "currency" },
          total_shareholder_yield_percent: { status: "missing", missing_inputs: ["spot_price"], unit: "percent" },
        },
      },
      {
        form_type: "10-K",
        period_end_date: "2026-09-30",
        filed_at: "2026-10-30",
        accession_number: "a",
        updated_at: "2026-11-01T00:00:00Z",
        base_metrics: {
          revenue: 2000,
          net_income: 300,
          gross_profit: 800,
        },
        derived_metrics: {
          free_cash_flow: { name: "Free Cash Flow", value: 250, unit: "USD", end: "2026-09-30", filed: null },
          owner_earnings: { name: "Owner Earnings", value: 220, unit: "USD", end: "2026-09-30", filed: null },
          gross_margin: { name: "Gross Margin", value: 0.4, unit: "ratio", end: "2026-09-30", filed: null },
          roe: { name: "Return on Equity", value: 0.2, unit: "ratio", end: "2026-09-30", filed: null },
          valuation: {
            status: "ready",
            inputs: { current_pe_percentile: 85 },
            scores: { valuation_formula: 1.7 },
            flags: { formula_gt_1_5: true, pe_percentile_above_80: true },
          },
          oe_dcf_total: { status: "ready", value: 500, unit: "currency" },
          oe_dcf_margin_of_safety_price: { status: "ready", value: 350, unit: "currency" },
          munger_20: { status: "ready", value: 480, unit: "currency" },
          eps_cagr_percent_points: { status: "ready", value: 12.3, unit: "percent_points" },
          peg_ratio: { status: "missing", missing_inputs: ["spot_price"], unit: "multiple" },
          cash_dividends: { status: "ready", value: 60, unit: "currency" },
          net_buyback_cash: { status: "ready", value: 40, unit: "currency" },
          dividend_payout_ratio_percent: { status: "ready", value: 20, unit: "percent" },
          total_shareholder_yield_percent: { status: "missing", missing_inputs: ["spot_price"], unit: "percent" },
          roic: { status: "ready", value: 13.1, unit: "percent" },
          ocf_to_net_income: { status: "ready", value: 1.2, unit: "multiple" },
          goodwill_to_equity_percent: { status: "missing", missing_inputs: ["goodwill"], unit: "percent" },
          book_effective_tax_rate_percent: { status: "ready", value: 22, unit: "percent" },
          gross_margin_percent: { status: "ready", value: 40, unit: "percent" },
          operating_margin_percent: { status: "ready", value: 25, unit: "percent" },
          net_margin_percent: { status: "ready", value: 15, unit: "percent" },
          revenue_3y_cagr_percent_points: { status: "ready", value: 10, unit: "percent_points" },
          revenue_yoy_percent: { status: "ready", value: 7.5, unit: "percent" },
        },
      },
      {
        form_type: "10-K",
        period_end_date: "2025-09-30",
        filed_at: "2025-10-30",
        accession_number: "b",
        updated_at: "2025-11-01T00:00:00Z",
        base_metrics: {
          revenue: 1500,
          net_income: 240,
        },
        derived_metrics: {
          free_cash_flow: { name: "Free Cash Flow", value: 210, unit: "USD", end: "2025-09-30", filed: null },
          oe_dcf_total: { status: "ready", value: 430, unit: "currency" },
        },
      },
    ],
  };

  const selectedFilings = selectDisplayFilings(financials);
  assert.deepEqual(
    selectedFilings.map((filing) => filing.form_type),
    ["10-Q", "10-K", "10-K"],
  );

  const points = buildTrendPoints(financials);
  assert.deepEqual(points.map((point) => point.label), ["2025 10-K", "2026 10-K", "2027 latest 10-Q"]);
  assert.equal(points[1].freeCashFlow, 250);
  assert.equal(hasIncompleteHistory(points), true);

  const scorecard = buildScorecard(financials);
  assert.equal(scorecard[0].label, "Revenue");
  assert.equal(scorecard[0].value, "US$800");
  assert.equal(scorecard[2].label, "Free Cash Flow");
  assert.equal(scorecard[2].value, "US$80");

  const rows = buildFilingRows(financials);
  assert.equal(rows[0].period, "2027 latest 10-Q");
  assert.equal(rows[0].rowKind, "provisional");
  assert.equal(rows[0].cells.oe_dcf_total, "US$120");
  assert.equal(rows[0].cells.total_shareholder_yield_percent, "Price pending");
  assert.equal(rows[1].period, "2026 10-K");
  assert.equal(rows[1].rowKind, "annual");
  assert.equal(rows[1].cells.revenue_3y_cagr_percent_points, "10.0pp");
  assert.equal(rows[1].cells.ocf_to_net_income, "1.20x");
});

test("not applicable cells render specific reasons instead of a generic placeholder", () => {
  const financials: FinancialsResponse = {
    ticker: "AAPL",
    cik: "0000320193",
    company: "Apple Inc.",
    status: "ready",
    updated_at: "2026-04-13T00:00:00Z",
    filings: [
      {
        form_type: "10-K",
        period_end_date: "2008-09-27",
        filed_at: "2008-11-05",
        accession_number: "a",
        updated_at: "2008-11-06T00:00:00Z",
        base_metrics: {},
        derived_metrics: {
          oe_dcf_total: { status: "not_applicable", metadata: { reason: "insufficient_history" }, unit: "currency" },
          cash_dividends: { status: "not_applicable", metadata: { reason: "no_dividends_paid" }, unit: "currency" },
          dividend_payout_ratio_percent: {
            status: "not_applicable",
            metadata: { reason: "no_dividends_paid" },
            unit: "percent",
          },
          peg_ratio: { status: "not_applicable", metadata: { reason: "CAGR <= 0" }, unit: "multiple" },
          revenue_yoy_percent: { status: "not_applicable", metadata: { reason: "prior_year == 0" }, unit: "percent" },
        },
      },
    ],
  };

  const [row] = buildFilingRows(financials);
  assert.equal(row.cells.oe_dcf_total, "Need history");
  assert.equal(row.cells.cash_dividends, "US$0");
  assert.equal(row.cells.dividend_payout_ratio_percent, "0.0%");
  assert.equal(row.cells.peg_ratio, "Neg. CAGR");
  assert.equal(row.cells.revenue_yoy_percent, "Prior year 0");
});

test("derived table columns expose grouped headers", () => {
  assert.ok(derivedTableColumns.length > 10);
  const groups = derivedColumnGroups();
  const total = groups.reduce((sum, group) => sum + group.count, 0);
  assert.equal(total, derivedTableColumns.length);
  assert.ok(groups.some((group) => group.name === "Valuation"));
  assert.ok(groups.some((group) => group.name === "Pricing Power"));
});

test("derived glossary stays aligned to column schema", () => {
  const glossary = buildDerivedGlossary();
  assert.equal(glossary.length, derivedTableColumns.length);
  const peg = glossary.find((item) => item.key === "peg_ratio");
  assert.ok(peg);
  assert.equal(peg?.formula, "PE / CAGR_percent_points");
  assert.match(peg?.missingRule ?? "", /Market data required/);
});
