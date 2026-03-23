"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  ChartData,
  ChartOptions,
  Filler,
  LineElement,
  LinearScale,
  PointElement,
  ScriptableContext,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";

import { priceSeries } from "@/lib/dashboard-data";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const data: ChartData<"line"> = {
  labels: [...priceSeries.labels],
  datasets: [
    {
      label: "Price",
      data: [...priceSeries.values],
      borderColor: "#5ff2ff",
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.35,
      fill: true,
      backgroundColor: (context: ScriptableContext<"line">) => {
        const chart = context.chart;
        const { ctx, chartArea } = chart;

        if (!chartArea) {
          return "rgba(95, 242, 255, 0.18)";
        }

        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, "rgba(95, 242, 255, 0.28)");
        gradient.addColorStop(1, "rgba(95, 242, 255, 0)");
        return gradient;
      },
    },
  ],
};

const options: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      intersect: false,
      displayColors: false,
      backgroundColor: "rgba(4, 8, 15, 0.96)",
      borderColor: "rgba(95, 242, 255, 0.25)",
      borderWidth: 1,
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
      padding: 12,
    },
  },
  interaction: {
    intersect: false,
    mode: "index" as const,
  },
  scales: {
    x: {
      grid: {
        color: "rgba(148, 163, 184, 0.08)",
      },
      ticks: {
        color: "#64748b",
      },
      border: {
        display: false,
      },
    },
    y: {
      grid: {
        color: "rgba(148, 163, 184, 0.08)",
      },
      ticks: {
        color: "#64748b",
      },
      border: {
        display: false,
      },
    },
  },
};

export function HeroChart() {
  return (
    <section className="animate-rise px-4 md:px-8" style={{ animationDelay: "160ms" }}>
      <div className="mx-auto max-w-6xl overflow-hidden rounded-[32px] border border-white/10 bg-black/15 p-5 shadow-panel backdrop-blur-2xl md:p-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Price history</p>
            <h2 className="mt-2 text-2xl font-semibold text-white md:text-3xl">10-year monthly price chart</h2>
          </div>
          <p className="max-w-md text-sm text-slate-400">
            A clean trendline for the staged template migration. The live version will point at SEC-synced data exposed by the Go gateway.
          </p>
        </div>
        <div className="h-[320px] md:h-[420px]">
          <Line data={data} options={options} />
        </div>
      </div>
    </section>
  );
}
