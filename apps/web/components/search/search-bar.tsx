export function SearchBar() {
  return (
    <header className="animate-rise px-4 pt-4 md:px-8 md:pt-8" style={{ animationDelay: "80ms" }}>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-cyan-glow/80">QuantumValue Terminal</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Historical DNA for public companies
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-400 md:text-base">
            Scan ten-year price behavior, core valuation markers, and filing-derived balance sheet history from one operating surface.
          </p>
        </div>
      </div>
      <div className="mx-auto mt-6 max-w-4xl">
        <label className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-black/25 px-4 py-4 shadow-panel backdrop-blur-xl transition focus-within:border-cyan-glow/40 focus-within:shadow-[0_0_45px_rgba(95,242,255,0.08)]">
          <svg className="h-5 w-5 text-slate-500 transition group-focus-within:text-cyan-glow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M10.75 18a7.25 7.25 0 1 1 0-14.5 7.25 7.25 0 0 1 0 14.5Z" />
          </svg>
          <input
            type="text"
            placeholder="Search tickers like AAPL, 0700.HK, 600519.SH"
            className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500 md:text-base"
          />
        </label>
      </div>
    </header>
  );
}
