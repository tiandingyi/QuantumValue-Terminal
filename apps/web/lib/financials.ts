export type FinancialMetricPayload = {
  name?: string;
  value?: number;
  unit?: string;
  end?: string;
  filed?: string | null;
  source?: string;
};

export type DerivedCellPayload = {
  status?: "ready" | "missing" | "not_applicable";
  value?: number | null;
  unit?: string;
  formula?: string;
  missing_inputs?: string[];
  lookback?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  metadata?: {
    message?: string;
    reason?: string;
    [key: string]: unknown;
  };
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
  derived_metrics: Record<string, FinancialMetricPayload | DerivedCellPayload | ValuationPayload | undefined>;
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
  rowKind: "annual" | "provisional";
  cells: Record<string, string>;
};

export type DerivedTableColumn = {
  key: string;
  label: string;
  group: "Valuation" | "Shareholder Returns" | "Quality / Risk" | "Pricing Power";
  displayType: "currency" | "percent" | "percent_points" | "multiple" | "flag";
  meaning: string;
  formula: string;
  missingRule: string;
};

export const derivedTableColumns: DerivedTableColumn[] = [
  {
    key: "oe_dcf_total",
    label: "OE-DCF",
    group: "Valuation",
    displayType: "currency",
    meaning: "Owner earnings discounted cash-flow intrinsic value per share.",
    formula: "PV_stage1 + PV_terminal + net_cash_per_share",
    missingRule: "Shows SEC fact unavailable when owner earnings history or share inputs are missing.",
  },
  {
    key: "oe_dcf_margin_of_safety_price",
    label: "OE-DCF MOS",
    group: "Valuation",
    displayType: "currency",
    meaning: "Discounted OE-DCF value with margin-of-safety haircut.",
    formula: "OE_DCF_total × (1 - margin_of_safety)",
    missingRule: "Shows SEC fact unavailable when OE-DCF cannot be computed.",
  },
  {
    key: "munger_20",
    label: "Munger 20x",
    group: "Valuation",
    displayType: "currency",
    meaning: "Horizon valuation using dividend PV and 20x exit multiple.",
    formula: "PV_dividends + exit_value_20 + net_cash_per_share",
    missingRule: "Shows SEC fact unavailable when owner-earnings growth inputs are insufficient.",
  },
  {
    key: "eps_cagr_percent_points",
    label: "EPS CAGR (pp)",
    group: "Valuation",
    displayType: "percent_points",
    meaning: "EPS growth rate over the selected lookback window.",
    formula: "(ending / beginning)^(1/n) - 1, stored as percentage points",
    missingRule: "Shows SEC fact unavailable if no valid EPS start/end window exists.",
  },
  {
    key: "peg_ratio",
    label: "PEG",
    group: "Valuation",
    displayType: "multiple",
    meaning: "P/E relative to EPS CAGR percent points.",
    formula: "PE / CAGR_percent_points",
    missingRule: "Shows Market data required when spot price is unavailable.",
  },
  {
    key: "cash_dividends",
    label: "Cash Dividends",
    group: "Shareholder Returns",
    displayType: "currency",
    meaning: "Cash distributed to shareholders in the filing period.",
    formula: "SEC dividends cash outflow facts",
    missingRule: "Shows Dividend data unavailable when dividend facts are absent.",
  },
  {
    key: "net_buyback_cash",
    label: "Net Buyback Cash",
    group: "Shareholder Returns",
    displayType: "currency",
    meaning: "Repurchase cash net of equity issuance cash.",
    formula: "buyback_cash - (equity_issuance_cash - minority_equity_issuance)",
    missingRule: "Defaults missing components to 0 and still returns a value.",
  },
  {
    key: "dividend_payout_ratio_percent",
    label: "Payout Ratio",
    group: "Shareholder Returns",
    displayType: "percent",
    meaning: "Share of net income paid out as dividends.",
    formula: "cash_dividends / net_income × 100",
    missingRule: "Shows Dividend data unavailable when dividends or net income are unavailable.",
  },
  {
    key: "total_shareholder_yield_percent",
    label: "Total Shareholder Yield",
    group: "Shareholder Returns",
    displayType: "percent",
    meaning: "Dividend yield plus net buyback yield.",
    formula: "(cash_dividends + net_buyback_cash) / market_cap × 100",
    missingRule: "Shows Market data required when spot price/market cap are unavailable.",
  },
  {
    key: "roic",
    label: "ROIC",
    group: "Quality / Risk",
    displayType: "percent",
    meaning: "Approximate return on invested capital after tax.",
    formula: "NOPAT / invested_capital × 100",
    missingRule: "Shows Not applicable when invested capital is non-positive.",
  },
  {
    key: "ocf_to_net_income",
    label: "OCF / Net Income",
    group: "Quality / Risk",
    displayType: "multiple",
    meaning: "Cash conversion multiple from earnings to operating cash.",
    formula: "operating_cash_flow / net_income",
    missingRule: "Shows SEC fact unavailable when OCF or net income is missing.",
  },
  {
    key: "goodwill_to_equity_percent",
    label: "Goodwill / Equity",
    group: "Quality / Risk",
    displayType: "percent",
    meaning: "Goodwill burden relative to equity base.",
    formula: "goodwill / equity_denominator × 100",
    missingRule: "Shows SEC fact unavailable when goodwill or equity denominator is missing.",
  },
  {
    key: "book_effective_tax_rate_percent",
    label: "Book ETR",
    group: "Quality / Risk",
    displayType: "percent",
    meaning: "Book effective tax burden versus pretax earnings.",
    formula: "income_tax_expense / EBT × 100",
    missingRule: "Shows SEC fact unavailable when tax expense or EBT is missing.",
  },
  {
    key: "gross_margin_percent",
    label: "Gross Margin",
    group: "Pricing Power",
    displayType: "percent",
    meaning: "Gross profit retained from each revenue dollar.",
    formula: "gross_profit / revenue × 100",
    missingRule: "Shows SEC fact unavailable when gross profit is missing; Not applicable when revenue <= 0.",
  },
  {
    key: "operating_margin_percent",
    label: "Operating Margin",
    group: "Pricing Power",
    displayType: "percent",
    meaning: "Operating income retained from revenue.",
    formula: "operating_income / revenue × 100",
    missingRule: "Shows SEC fact unavailable when operating income is missing; Not applicable when revenue <= 0.",
  },
  {
    key: "net_margin_percent",
    label: "Net Margin",
    group: "Pricing Power",
    displayType: "percent",
    meaning: "Net income retained from revenue.",
    formula: "net_income / revenue × 100",
    missingRule: "Shows SEC fact unavailable when net income is missing; Not applicable when revenue <= 0.",
  },
  {
    key: "revenue_3y_cagr_percent_points",
    label: "Revenue CAGR 3Y (pp)",
    group: "Pricing Power",
    displayType: "percent_points",
    meaning: "Revenue growth speed over approximately three years.",
    formula: "(revenue_end / revenue_start)^(1/n) - 1, stored as percentage points",
    missingRule: "Shows SEC fact unavailable when history window is insufficient.",
  },
  {
    key: "revenue_yoy_percent",
    label: "Revenue YoY",
    group: "Pricing Power",
    displayType: "percent",
    meaning: "Year-over-year revenue trend.",
    formula: "(current_year - prior_year) / prior_year × 100",
    missingRule: "Shows SEC fact unavailable when prior-year value is missing.",
  },
];

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
    rowKind: filing.form_type === "10-K" ? "annual" : "provisional",
    cells: Object.fromEntries(
      derivedTableColumns.map((column) => [column.key, formatDerivedMetricCell(filing, column)]),
    ),
  }));
}

export function hasIncompleteHistory(points: TrendPoint[]): boolean {
  return points.length < 10;
}

function derivedValue(filing: FilingSnapshot, key: string): number | null {
  const payload = filing.derived_metrics[key] as FinancialMetricPayload | undefined;
  return numberField(payload?.value);
}

export function derivedColumnGroups(): Array<{ name: DerivedTableColumn["group"]; count: number }> {
  const counts = new Map<DerivedTableColumn["group"], number>();
  for (const column of derivedTableColumns) {
    counts.set(column.group, (counts.get(column.group) ?? 0) + 1);
  }
  return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
}

export function buildDerivedGlossary(): Array<{
  key: string;
  label: string;
  group: DerivedTableColumn["group"];
  meaning: string;
  formula: string;
  missingRule: string;
}> {
  return derivedTableColumns.map((column) => ({
    key: column.key,
    label: column.label,
    group: column.group,
    meaning: column.meaning,
    formula: column.formula,
    missingRule: column.missingRule,
  }));
}

function formatDerivedMetricCell(filing: FilingSnapshot, column: DerivedTableColumn): string {
  const payload = filing.derived_metrics[column.key] as DerivedCellPayload | FinancialMetricPayload | undefined;
  if (!payload) {
    return "SEC fact unavailable";
  }

  const status = (payload as DerivedCellPayload).status;
  if (status === "missing") {
    return missingReasonLabel((payload as DerivedCellPayload).missing_inputs ?? []);
  }
  if (status === "not_applicable") {
    return notApplicableReasonLabel(column, payload as DerivedCellPayload);
  }

  const value = numberField(payload.value);
  if (value === null) {
    return "SEC fact unavailable";
  }

  switch (column.displayType) {
    case "currency":
      return formatCurrency(value);
    case "percent":
      return `${value.toFixed(1)}%`;
    case "percent_points":
      return `${value.toFixed(1)}pp`;
    case "multiple":
      return `${value.toFixed(2)}x`;
    case "flag":
      return value >= 1 ? "Risk flagged" : "No flag";
    default:
      return String(value);
  }
}

function missingReasonLabel(missingInputs: string[]): string {
  const keys = new Set(missingInputs);
  if (keys.has("spot_price") || keys.has("market_cap")) {
    return "Price pending";
  }
  if (keys.has("cash_dividends") && missingInputs.length === 1) {
    return "Dividend pending";
  }
  if (missingInputs.length > 0) {
    const fields = missingInputs.slice(0, 2).join(", ");
    return `Need ${fields}`;
  }
  return "Data pending";
}

function notApplicableReasonLabel(column: DerivedTableColumn, payload: DerivedCellPayload): string {
  const reason = payload.metadata?.reason ?? "";
  if (reason === "no_dividends_paid") {
    if (column.displayType === "currency") {
      return formatCurrency(0);
    }
    if (column.displayType === "percent" || column.displayType === "percent_points") {
      return "0.0%";
    }
  }

  switch (reason) {
    case "spot_price_unavailable":
      return "Price pending";
    case "market_cap_unavailable":
      return "Cap pending";
    case "pe_ratio_not_applicable":
      return "PE pending";
    case "eps_cagr_not_applicable":
      return "Growth pending";
    case "CAGR <= 0":
      return "Neg. CAGR";
    case "CAGR+DivYield <= 0":
      return "Neg. growth+yld";
    case "invested_capital <= 0":
      return "Neg. capital";
    case "insufficient_history":
      return "Need history";
    case "no_positive_eps_baseline":
      return "No EPS base";
    case "prior_year == 0":
      return "Prior year 0";
    case "EPS_for_PE <= 0":
      return "EPS <= 0";
    default:
      return "N/M";
  }
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
