import { marketSegments } from "@/lib/dashboard-data";

const icons = [
  <path key="us" d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2Zm0 0V9a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v10m-6 0a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2m0 0V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2Z" />,
  <path key="hk" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />,
  <path key="a" d="M13 10V3L4 14h7v7l9-11h-7z" />,
  <path key="funds" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />,
  <path key="global" d="M3.055 11H5a2 2 0 0 1 2 2v1a2 2 0 0 0 2 2 2 2 0 0 1 2 2v2.945M8 3.935V5.5A2.5 2.5 0 0 0 10.5 8h.5a2 2 0 0 1 2 2 2 2 0 1 0 4 0 2 2 0 0 1 2-2h1.064M15 20.488V18a2 2 0 0 1 2-2h3.064" />,
];

export function Sidebar() {
  return (
    <aside className="sticky top-0 flex h-svh w-full flex-row items-center justify-between border-b border-white/10 bg-black/25 px-5 py-4 backdrop-blur-xl md:h-svh md:w-24 md:flex-col md:justify-start md:gap-7 md:border-b-0 md:border-r md:px-0 md:py-8">
      <div className="hidden text-[10px] uppercase tracking-[0.35em] text-cyan-glow/80 md:block">
        QVT
      </div>
      <div className="flex flex-row gap-3 md:flex-col">
        {marketSegments.map((segment, index) => (
          <button
            key={segment.label}
            className={`group flex h-12 w-12 items-center justify-center rounded-2xl border transition duration-300 ${
              segment.active
                ? "border-cyan-glow/40 bg-cyan-glow/10 text-cyan-glow shadow-[0_0_30px_rgba(95,242,255,0.16)]"
                : "border-white/5 bg-white/[0.03] text-slate-500 hover:border-white/15 hover:text-slate-200"
            }`}
            type="button"
            aria-label={segment.label}
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.7">
              {icons[index]}
            </svg>
          </button>
        ))}
      </div>
      <div className="hidden rotate-180 text-[10px] uppercase tracking-[0.35em] text-slate-500 [writing-mode:vertical-rl] md:block">
        U.S. filings only
      </div>
    </aside>
  );
}
