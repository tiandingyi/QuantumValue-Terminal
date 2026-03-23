import { matrixRows } from "@/lib/dashboard-data";

export function FinancialMatrix() {
  return (
    <section className="animate-rise px-4 pb-10 md:px-8 md:pb-14" style={{ animationDelay: "320ms" }}>
      <div className="mx-auto max-w-6xl overflow-hidden rounded-[32px] border border-white/10 bg-black/15 shadow-panel backdrop-blur-2xl">
        <div className="flex flex-col gap-3 border-b border-white/10 px-5 py-5 md:flex-row md:items-end md:justify-between md:px-8">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Financial matrix</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Master financial matrix</h2>
          </div>
          <p className="max-w-xl text-sm text-slate-400">
            The first migration keeps the original template’s wide-format table, but moves it into typed React markup that can later hydrate from JSONB payloads.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm text-slate-300">
            <thead>
              <tr className="text-xs uppercase tracking-[0.24em] text-slate-500">
                <th className="sticky left-0 bg-[#05070c] px-5 py-4 md:px-8">Year</th>
                <th className="px-5 py-4 text-right md:px-6">Revenue</th>
                <th className="px-5 py-4 text-right md:px-6">Net income</th>
                <th className="px-5 py-4 text-right md:px-6">EPS</th>
                <th className="px-5 py-4 text-right md:px-6">Assets</th>
                <th className="px-5 py-4 text-right md:px-8">Liabilities</th>
              </tr>
            </thead>
            <tbody className="font-mono text-sm">
              {matrixRows.map((row, index) => (
                <tr key={row.year} className={index % 2 === 0 ? "bg-white/[0.03]" : "bg-transparent"}>
                  <td className="sticky left-0 bg-inherit px-5 py-4 text-slate-100 md:px-8">{row.year}</td>
                  <td className="px-5 py-4 text-right md:px-6">{row.revenue}</td>
                  <td className="px-5 py-4 text-right md:px-6">{row.netIncome}</td>
                  <td className="px-5 py-4 text-right md:px-6">{row.eps}</td>
                  <td className="px-5 py-4 text-right md:px-6">{row.assets}</td>
                  <td className="px-5 py-4 text-right md:px-8">{row.liabilities}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
