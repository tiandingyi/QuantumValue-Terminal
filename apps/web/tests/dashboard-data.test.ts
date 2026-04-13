import assert from "node:assert/strict";
import test from "node:test";

import { metricCards, priceSeries } from "../lib/dashboard-data";
import {
  FinancialsResponse,
  buildScorecard,
  buildTrendPoints,
  hasIncompleteHistory,
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
        form_type: "10-K",
        period_end_date: "2026-09-30",
        filed_at: "2026-10-30",
        accession_number: "a",
        updated_at: "2026-11-01T00:00:00Z",
        base_metrics: {
          revenue: 2000,
          net_income: 300,
        },
        derived_metrics: {
          free_cash_flow: { name: "Free Cash Flow", value: 250, unit: "USD", end: "2026-09-30", filed: null },
          owner_earnings: { name: "Owner Earnings", value: 220, unit: "USD", end: "2026-09-30", filed: null },
          valuation: {
            status: "ready",
            inputs: { current_pe_percentile: 85 },
            scores: { valuation_formula: 1.7 },
            flags: { formula_gt_1_5: true, pe_percentile_above_80: true },
          },
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
        },
      },
    ],
  };

  const points = buildTrendPoints(financials);
  assert.deepEqual(points.map((point) => point.label), ["2025", "2026"]);
  assert.equal(points[1].freeCashFlow, 250);
  assert.equal(hasIncompleteHistory(points), true);

  const scorecard = buildScorecard(financials);
  assert.equal(scorecard[0].value, "85%");
  assert.equal(scorecard[1].value, "$220");
  assert.equal(scorecard[2].value, "1.70");
});
