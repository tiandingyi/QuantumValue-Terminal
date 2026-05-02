"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CategoryScale,
  Chart as ChartJS,
  ChartData,
  ChartOptions,
  Filler,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";

import {
  derivedColumnGroups,
  derivedTableColumns,
  buildDerivedGlossary,
  FinancialsResponse,
  buildFilingRows,
  buildScorecard,
  buildTrendPoints,
  formatChartCurrency,
  hasIncompleteHistory,
} from "@/lib/financials";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const apiBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

const chartOptions: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: "index",
  },
  plugins: {
    legend: {
      labels: {
        color: "#cbd5e1",
        boxWidth: 10,
        boxHeight: 10,
        usePointStyle: true,
      },
    },
    tooltip: {
      intersect: false,
      displayColors: false,
      backgroundColor: "rgba(4, 8, 15, 0.96)",
      borderColor: "rgba(34, 211, 238, 0.25)",
      borderWidth: 1,
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
      padding: 12,
    },
  },
  scales: {
    x: {
      grid: { color: "rgba(148, 163, 184, 0.08)" },
      ticks: { color: "#64748b" },
      border: { display: false },
    },
    y: {
      grid: { color: "rgba(148, 163, 184, 0.08)" },
      ticks: {
        color: "#64748b",
        callback: (value) => formatChartCurrency(typeof value === "number" ? value : Number(value)),
      },
      border: { display: false },
    },
  },
};

type ArchaeologyDashboardProps = {
  activeTicker: string;
  refreshToken: number;
};

export function ArchaeologyDashboard({ activeTicker, refreshToken }: ArchaeologyDashboardProps) {
  const [financials, setFinancials] = useState<FinancialsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadFinancials() {
      setIsLoading(true);
      setError(null);
      setFinancials(null);

      try {
        const response = await fetch(`${apiBaseURL}/api/v1/financials/${activeTicker}`, {
          method: "GET",
        });
        const payload = await response.json();

        if (response.status === 202) {
          if (!isMounted) {
            return;
          }
          setFinancials(null);
          setError("Mining started. Sync status will update when filings are ready.");
          return;
        }

        if (!response.ok) {
          throw new Error(payload.message || "Financials endpoint is unavailable.");
        }

        if (!isMounted) {
          return;
        }
        setFinancials(payload as FinancialsResponse);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setFinancials(null);
        setError(loadError instanceof Error ? loadError.message : "Unable to load financial history.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadFinancials();

    return () => {
      isMounted = false;
    };
  }, [activeTicker, refreshToken]);

  const trendPoints = useMemo(() => (financials ? buildTrendPoints(financials) : []), [financials]);
  const scorecard = useMemo(() => (financials ? buildScorecard(financials) : []), [financials]);
  const filingRows = useMemo(() => (financials ? buildFilingRows(financials) : []), [financials]);
  const columnGroups = useMemo(() => derivedColumnGroups(), []);
  const metricGlossary = useMemo(() => buildDerivedGlossary(), []);
  const incompleteHistory = financials ? hasIncompleteHistory(trendPoints) : false;

  const revenueChartData = useMemo<ChartData<"line">>(
    () => ({
      labels: trendPoints.map((point) => point.label),
      datasets: [
        {
          label: "Revenue",
          data: trendPoints.map((point) => point.revenue),
          borderColor: "#5ff2ff",
          backgroundColor: "rgba(95, 242, 255, 0.12)",
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.35,
          fill: true,
        },
        {
          label: "Net income",
          data: trendPoints.map((point) => point.netIncome),
          borderColor: "#a7f3d0",
          backgroundColor: "rgba(167, 243, 208, 0.08)",
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.35,
        },
      ],
    }),
    [trendPoints],
  );

  const cashFlowChartData = useMemo<ChartData<"line">>(
    () => ({
      labels: trendPoints.map((point) => point.label),
      datasets: [
        {
          label: "Free cash flow",
          data: trendPoints.map((point) => point.freeCashFlow),
          borderColor: "#facc15",
          backgroundColor: "rgba(250, 204, 21, 0.1)",
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.35,
          fill: true,
        },
      ],
    }),
    [trendPoints],
  );

  return (
    <section className="animate-rise px-4 md:px-8" data-testid="archaeology-dashboard" style={{ animationDelay: "160ms" }}>
      <div className="mx-auto max-w-6xl border-y border-white/10 py-7 md:py-9">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-cyan-glow/75">Financial archaeology</p>
            <h2 className="mt-2 text-2xl font-semibold text-white md:text-3xl">
              {financials ? `${financials.company} filings` : `${activeTicker} filings`}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Revenue, earnings, cash generation, and balance sheet signals from the Go Gateway JSONB feed.
            </p>
          </div>
          <div className="border border-white/10 bg-black/25 px-4 py-3 text-sm text-slate-300" data-testid="active-ticker">
            Active ticker: <span className="font-mono text-cyan-glow">{activeTicker}</span>
          </div>
        </div>

        {isLoading ? <LoadingState /> : null}

        {!isLoading && error ? (
          <div className="mt-8 border border-amber-300/20 bg-amber-300/5 px-4 py-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        {!isLoading && financials && trendPoints.length > 0 ? (
          <>
            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <ChartPanel title="Revenue vs. Net Income" data={revenueChartData} />
              <ChartPanel title="Free Cash Flow" data={cashFlowChartData} />
            </div>

            {incompleteHistory ? (
              <div className="mt-5 border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-300">
                Showing annual 10-K history plus the latest 10-Q when the newest year has not filed a 10-K yet. More annual points will appear as filings are cached.
              </div>
            ) : null}

            <div className="mt-8 grid gap-x-8 gap-y-6 md:grid-cols-3">
              {scorecard.map((metric) => (
                <div key={metric.label} className="border-t border-white/10 pt-5">
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-glow/75">{metric.label}</p>
                  <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{metric.value}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">{metric.detail}</p>
                </div>
              ))}
            </div>

            <div className="mt-8 overflow-x-auto border border-white/10 bg-black/15" data-testid="filing-history">
              <table className="min-w-full border-collapse text-left text-sm">
                <thead className="border-b border-white/10 text-xs uppercase tracking-[0.22em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium" rowSpan={2}>
                      Year
                    </th>
                    <th className="px-4 py-3 font-medium" rowSpan={2}>
                      Filing
                    </th>
                    <th className="px-4 py-3 font-medium" rowSpan={2}>
                      Filed
                    </th>
                    {columnGroups.map((group) => (
                      <th key={group.name} className="px-4 py-3 text-center font-medium" colSpan={group.count}>
                        {group.name}
                      </th>
                    ))}
                  </tr>
                  <tr>
                    {derivedTableColumns.map((column) => (
                      <th key={column.key} className="px-4 py-3 font-medium">
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filingRows.map((row) => (
                    <tr key={`${row.period}-${row.filedAt}`} className="border-b border-white/5 last:border-0">
                      <td className="px-4 py-3 font-mono text-cyan-glow">{row.period}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {row.rowKind === "annual" ? row.formType : `${row.formType} (provisional)`}
                      </td>
                      <td className="px-4 py-3 text-slate-400">{row.filedAt}</td>
                      {derivedTableColumns.map((column) => (
                        <td key={column.key} className="px-4 py-3 text-slate-200">
                          {row.cells[column.key]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-8 border border-white/10 bg-black/15 p-4 md:p-6" data-testid="metric-glossary">
              <p className="text-xs uppercase tracking-[0.24em] text-cyan-glow/75">Metric glossary</p>
              <h3 className="mt-2 text-xl font-semibold text-white">Meaning and formulas</h3>
              <p className="mt-2 text-sm text-slate-400">
                Each metric below matches a table column. Missing states are explicit and never replaced with fabricated
                zeros.
              </p>
              <div className="mt-4 space-y-4">
                {metricGlossary.map((item) => (
                  <div key={item.key} className="border-t border-white/10 pt-4">
                    <p className="text-sm font-semibold text-white">
                      {item.label} <span className="text-xs font-normal text-slate-500">({item.group})</span>
                    </p>
                    <p className="mt-1 text-sm text-slate-300">{item.meaning}</p>
                    <p className="mt-1 font-mono text-xs text-cyan-glow/80">Formula: {item.formula}</p>
                    <p className="mt-1 text-xs text-slate-500">Missing rule: {item.missingRule}</p>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}

        {!isLoading && financials && trendPoints.length === 0 ? (
          <div className="mt-8 border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-300">
            No chartable financial metrics are available yet. Sync another filing or inspect the parser status.
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ChartPanel({ title, data }: { title: string; data: ChartData<"line"> }) {
  return (
    <div className="min-h-[340px] border border-white/10 bg-black/15 p-4 backdrop-blur-xl">
      <h3 className="text-sm uppercase tracking-[0.22em] text-slate-400">{title}</h3>
      <div className="mt-4 h-[280px]">
        <Line data={data} options={chartOptions} />
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="mt-8 grid gap-6 lg:grid-cols-2">
      <div className="h-[340px] animate-pulse bg-white/[0.04]" />
      <div className="h-[340px] animate-pulse bg-white/[0.04]" />
    </div>
  );
}
