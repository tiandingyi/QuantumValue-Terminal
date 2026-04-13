export type FinancialMetricPayload = {
  name?: string;
  value?: number;
  unit?: string;
  end?: string;
  filed?: string | null;
  source?: string;
};

export type ValuationPayload = {
  status?: string;
  missing_inputs?: string[];
  inputs?: {
    current_pe_percentile?: number | null;
    current_static_pe?: number | null;
    net_income_10y_cagr?: number | null;
    avg_tax_after_dividend_yield?: number | null;
  };
  scores?: {
    valuation_formula?: number;
  };
  flags?: {
    formula_gt_1_5?: boolean;
    pe_percentile_above_80?: boolean;
  };
};

export type FilingSnapshot = {
  form_type: string;
  period_end_date: string;
  filed_at: string;
  accession_number: string;
  base_metrics: Record<string, number | string | null | Record<string, string>>;
  derived_metrics: Record<string, FinancialMetricPayload | ValuationPayload | undefined>;
  updated_at: string;
};

export type FinancialsResponse = {
  ticker: string;
  cik: string;
  company: string;
  status: string;
  updated_at: string;
  filings: FilingSnapshot[];
};

export type TrendPoint = {
  label: string;
  revenue: number | null;
  netIncome: number | null;
  freeCashFlow: number | null;
};

export type ScorecardMetric = {
  label: string;
  value: string;
  detail: string;
};

export function buildTrendPoints(financials: FinancialsResponse): TrendPoint[] {
  return financials.filings
    .map((filing) => ({
      label: filing.period_end_date.slice(0, 4),
      revenue: numberField(filing.base_metrics.revenue),
      netIncome: numberField(filing.base_metrics.net_income),
      freeCashFlow: derivedValue(filing, "free_cash_flow"),
    }))
    .filter((point) => point.revenue !== null || point.netIncome !== null || point.freeCashFlow !== null)
    .reverse();
}

export function buildScorecard(financials: FinancialsResponse): ScorecardMetric[] {
  const latest = financials.filings[0];
  const valuation = latest?.derived_metrics.valuation as ValuationPayload | undefined;
  const ownerEarnings = latest ? derivedValue(latest, "owner_earnings") : null;
  const formulaScore = valuation?.scores?.valuation_formula;
  const pePercentile = valuation?.inputs?.current_pe_percentile;
  const missingInputs = valuation?.missing_inputs ?? [];

  return [
    {
      label: "P/E Percentile",
      value: formatPercentile(pePercentile),
      detail:
        pePercentile === null || pePercentile === undefined
          ? missingDetail(missingInputs, "historical_pe_ratios")
          : "Position versus historical P/E baseline",
    },
    {
      label: "Owner Earnings",
      value: formatCurrency(ownerEarnings),
      detail:
        ownerEarnings === null
          ? "Waiting for net income, depreciation, and capex"
          : "Net income plus D&A less maintenance capex proxy",
    },
    {
      label: "Formula Score",
      value: formatRatio(formulaScore),
      detail:
        formulaScore === null || formulaScore === undefined
          ? missingDetail(missingInputs, "current_static_pe")
          : "(10Y CAGR + dividend yield) / static P/E",
    },
  ];
}

export function hasIncompleteHistory(points: TrendPoint[]): boolean {
  return points.length < 10;
}

function derivedValue(filing: FilingSnapshot, key: string): number | null {
  const payload = filing.derived_metrics[key] as FinancialMetricPayload | undefined;
  return numberField(payload?.value);
}

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return "Pending";
  }
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (absolute >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${value.toFixed(0)}`;
}

function formatPercentile(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return `${value.toFixed(0)}%`;
}

function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return value.toFixed(2);
}

function missingDetail(missingInputs: string[], primaryInput: string): string {
  if (missingInputs.includes(primaryInput)) {
    return "Market data input required";
  }
  return "Waiting for complete historical filings";
}
