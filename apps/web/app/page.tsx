import { FinancialMatrix } from "@/components/dashboard/financial-matrix";
import { HeroChart } from "@/components/dashboard/hero-chart";
import { MetricStrip } from "@/components/dashboard/metric-strip";
import { StackStatus } from "@/components/dashboard/stack-status";
import { Sidebar } from "@/components/layout/sidebar";
import { SearchBar } from "@/components/search/search-bar";

export default function Home() {
  return (
    <main className="min-h-screen bg-radial-terminal">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(95,242,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(95,242,255,0.04)_1px,transparent_1px)] bg-[size:80px_80px] opacity-25 [mask-image:radial-gradient(circle_at_center,black,transparent_78%)]" />
      <div className="absolute inset-x-0 top-0 h-64 bg-[radial-gradient(circle_at_top,rgba(95,242,255,0.16),transparent_60%)]" />
      <div className="relative z-10 md:flex">
        <Sidebar />
        <div className="flex-1">
          <SearchBar />
          <div className="space-y-8 md:space-y-10">
            <HeroChart />
            <MetricStrip />
            <StackStatus />
            <FinancialMatrix />
          </div>
        </div>
      </div>
    </main>
  );
}
