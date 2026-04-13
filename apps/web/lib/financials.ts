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

export function buildTrendPoints(financials: FinancialsResponse): TrendPoint[] {
  return financials.filings
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
  const latest = financials.filings[0];
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
  return financials.filings.slice(0, 20).map((filing) => ({
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

function formatPercent(value: number | null): string {
  if (value === null) {
    return "Pending";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatPeriodLabel(filing: FilingSnapshot): string {
  if (filing.form_type === "10-K") {
    return `${filing.period_end_date.slice(0, 4)} FY`;
  }

  const month = Number(filing.period_end_date.slice(5, 7));
  if (!Number.isFinite(month) || month < 1 || month > 12) {
    return filing.period_end_date.slice(0, 4);
  }
  const quarter = Math.floor((month - 1) / 3) + 1;
  return `${filing.period_end_date.slice(0, 4)} Q${quarter}`;
}
