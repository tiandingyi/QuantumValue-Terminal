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

export type FilingRow = {
  period: string;
  formType: string;
  filedAt: string;
  revenue: string;
  netIncome: string;
  freeCashFlow: string;
  ownerEarnings: string;
};

export function selectDisplayFilings(financials: FinancialsResponse): FilingSnapshot[] {
  const annualFilings = financials.filings.filter((filing) => filing.form_type === "10-K");
  const annualYears = new Set(annualFilings.map((filing) => filing.period_end_date.slice(0, 4)));
  const latestFiling = financials.filings[0];

  if (!latestFiling) {
    return [];
  }

  const latestYear = latestFiling.period_end_date.slice(0, 4);
  const includeLatestQuarter = latestFiling.form_type !== "10-K" && !annualYears.has(latestYear);
  const selected = includeLatestQuarter ? [latestFiling, ...annualFilings] : annualFilings;

  return selected.sort((left, right) => right.period_end_date.localeCompare(left.period_end_date));
}

export function buildTrendPoints(financials: FinancialsResponse): TrendPoint[] {
  return selectDisplayFilings(financials)
    .map((filing) => ({
      label: formatPeriodLabel(filing),
      revenue: numberField(filing.base_metrics.revenue),
      netIncome: numberField(filing.base_metrics.net_income),
      freeCashFlow: derivedValue(filing, "free_cash_flow"),
    }))
    .filter((point) => point.revenue !== null || point.netIncome !== null || point.freeCashFlow !== null)
    .reverse();
}

export function buildScorecard(financials: FinancialsResponse): ScorecardMetric[] {
  const latest = selectDisplayFilings(financials)[0];
  if (!latest) {
    return [];
  }

  const revenue = numberField(latest.base_metrics.revenue);
  const netIncome = numberField(latest.base_metrics.net_income);
  const freeCashFlow = derivedValue(latest, "free_cash_flow");
  const ownerEarnings = latest ? derivedValue(latest, "owner_earnings") : null;
  const grossMargin = derivedValue(latest, "gross_margin");
  const roe = derivedValue(latest, "roe");

  return [
    revenue === null
      ? null
      : {
          label: "Revenue",
          value: formatCurrency(revenue),
          detail: "Latest SEC filing revenue",
        },
    netIncome === null
      ? null
      : {
          label: "Net Income",
          value: formatCurrency(netIncome),
          detail: "Latest SEC filing earnings",
        },
    freeCashFlow === null
      ? null
      : {
          label: "Free Cash Flow",
          value: formatCurrency(freeCashFlow),
          detail: "Operating cash flow less capex",
        },
    ownerEarnings === null
      ? null
      : {
          label: "Owner Earnings",
          value: formatCurrency(ownerEarnings),
          detail: "Net income plus D&A less maintenance capex proxy",
        },
    grossMargin === null
      ? null
      : {
          label: "Gross Margin",
          value: formatPercent(grossMargin),
          detail: "Gross profit divided by revenue",
        },
    roe === null
      ? null
      : {
          label: "ROE",
          value: formatPercent(roe),
          detail: "Net income divided by shareholders equity",
        },
  ].filter((metric): metric is ScorecardMetric => metric !== null);
}

export function buildFilingRows(financials: FinancialsResponse): FilingRow[] {
  return selectDisplayFilings(financials).slice(0, 20).map((filing) => ({
    period: formatPeriodLabel(filing),
    formType: filing.form_type,
    filedAt: filing.filed_at,
    revenue: formatCurrency(numberField(filing.base_metrics.revenue)),
    netIncome: formatCurrency(numberField(filing.base_metrics.net_income)),
    freeCashFlow: formatCurrency(derivedValue(filing, "free_cash_flow")),
    ownerEarnings: formatCurrency(derivedValue(filing, "owner_earnings")),
  }));
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
  return formatCompactCurrency(value, "US$");
}

export function formatChartCurrency(value: number | null): string {
  return formatCompactCurrency(value, "$");
}

function formatCompactCurrency(value: number | null, prefix: string): string {
  if (value === null) {
    return "Pending";
  }
  const absolute = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (absolute >= 1_000_000_000) {
    return `${sign}${prefix}${trimTrailingZero(absolute / 1_000_000_000)}B`;
  }
  if (absolute >= 1_000_000) {
    return `${sign}${prefix}${trimTrailingZero(absolute / 1_000_000)}M`;
  }
  if (absolute >= 1_000) {
    return `${sign}${prefix}${trimTrailingZero(absolute / 1_000)}K`;
  }
  return `${sign}${prefix}${absolute.toFixed(0)}`;
}

function trimTrailingZero(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "Pending";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatPeriodLabel(filing: FilingSnapshot): string {
  if (filing.form_type === "10-K") {
    return `${filing.period_end_date.slice(0, 4)} 10-K`;
  }

  return `${filing.period_end_date.slice(0, 4)} latest 10-Q`;
}
