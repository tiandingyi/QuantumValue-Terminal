"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type SyncPayload = {
  ticker: string;
  status: string;
  message: string;
  updated_at: string;
};

const apiBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

export function SearchBar() {
  const [ticker, setTicker] = useState("AAPL");
  const [syncStatus, setSyncStatus] = useState<SyncPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  async function pollStatus(activeTicker: string) {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${apiBaseURL}/api/v1/status/${activeTicker}`, {
          method: "GET",
        });

        const payload = (await response.json()) as SyncPayload;
        setSyncStatus(payload);

        if (response.status === 200 || payload.status === "SUCCESS") {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
          setIsSubmitting(false);
        }
      } catch {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        setIsSubmitting(false);
        setError("Polling failed. Check that the Go gateway and Python engine are running.");
      }
    }, 1500);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      setError("Please enter a ticker symbol.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    setSyncStatus(null);

    try {
      const response = await fetch(`${apiBaseURL}/api/v1/sync/${normalizedTicker}`, {
        method: "POST",
      });
      const payload = (await response.json()) as SyncPayload;

      if (!response.ok && response.status !== 202) {
        throw new Error(payload.message || "Unable to trigger sync.");
      }

      setSyncStatus(payload);

      if (response.status === 202 || payload.status === "IN_PROGRESS") {
        await pollStatus(normalizedTicker);
        return;
      }

      setIsSubmitting(false);
    } catch (submitError) {
      setIsSubmitting(false);
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Unable to trigger sync. Check that the local stack is running.",
      );
    }
  }

  const statusTone =
    syncStatus?.status === "SUCCESS"
      ? "bg-emerald-500/15 text-emerald-300"
      : "bg-cyan-glow/15 text-cyan-glow";

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
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-black/25 px-4 py-4 shadow-panel backdrop-blur-xl transition focus-within:border-cyan-glow/40 focus-within:shadow-[0_0_45px_rgba(95,242,255,0.08)]">
            <svg className="h-5 w-5 text-slate-500 transition group-focus-within:text-cyan-glow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M10.75 18a7.25 7.25 0 1 1 0-14.5 7.25 7.25 0 0 1 0 14.5Z" />
            </svg>
            <input
              type="text"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
              placeholder="Search tickers like AAPL, 0700.HK, 600519.SH"
              className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500 md:text-base"
            />
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl border border-cyan-glow/30 bg-cyan-glow/10 px-4 py-2 text-xs font-medium uppercase tracking-[0.24em] text-cyan-glow transition hover:bg-cyan-glow/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Mining" : "Sync"}
            </button>
          </label>

          <div className="grid gap-3 md:grid-cols-[auto_1fr] md:items-center">
            <div className={`inline-flex w-fit rounded-full px-3 py-1 text-xs uppercase tracking-[0.22em] ${statusTone}`}>
              {syncStatus?.status ?? "idle"}
            </div>
            <p className="text-sm text-slate-400">
              {syncStatus?.message ??
                "Enter a ticker and press Sync to trigger the mock end-to-end handshake through Go and Python."}
            </p>
          </div>

          {syncStatus?.ticker ? (
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
              Active ticker: {syncStatus.ticker} · Last update: {new Date(syncStatus.updated_at).toLocaleTimeString()}
            </p>
          ) : null}

          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        </form>
      </div>
    </header>
  );
}
