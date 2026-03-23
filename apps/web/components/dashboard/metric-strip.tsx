import { metricCards } from "@/lib/dashboard-data";

export function MetricStrip() {
  return (
    <section className="animate-rise px-4 md:px-8" style={{ animationDelay: "240ms" }}>
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-x-8 gap-y-6 border-y border-white/10 py-8 md:grid-cols-2 xl:grid-cols-3">
        {metricCards.map((metric) => (
          <div key={metric.label} className="flex min-h-24 flex-col justify-between">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm uppercase tracking-[0.24em] text-cyan-glow/75">{metric.label}</h3>
              <span className="h-px flex-1 bg-gradient-to-r from-white/0 via-white/10 to-white/0" />
            </div>
            <p className="mt-4 text-4xl font-semibold tracking-tight text-white">{metric.value}</p>
            <p className="mt-2 max-w-xs text-sm leading-6 text-slate-500">{metric.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
