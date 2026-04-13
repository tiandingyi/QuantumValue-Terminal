"use client";

import { useState } from "react";

import { ArchaeologyDashboard } from "@/components/dashboard/archaeology-dashboard";
import { SearchBar } from "@/components/search/search-bar";

export function TerminalWorkspace() {
  const [activeTicker, setActiveTicker] = useState("AAPL");
  const [refreshToken, setRefreshToken] = useState(0);

  function handleSyncComplete(ticker: string) {
    setActiveTicker(ticker);
    setRefreshToken((current) => current + 1);
  }

  return (
    <>
      <SearchBar activeTicker={activeTicker} onTickerSelected={setActiveTicker} onSyncComplete={handleSyncComplete} />
      <div className="space-y-8 md:space-y-10">
        <ArchaeologyDashboard activeTicker={activeTicker} refreshToken={refreshToken} />
      </div>
    </>
  );
}
