"use client";

import { useState } from "react";

import { ArchaeologyDashboard } from "@/components/dashboard/archaeology-dashboard";
import { StackStatus } from "@/components/dashboard/stack-status";
import { SearchBar } from "@/components/search/search-bar";

export function TerminalWorkspace() {
  const [activeTicker, setActiveTicker] = useState("AAPL");

  return (
    <div className="flex-1">
      <SearchBar activeTicker={activeTicker} onTickerSelected={setActiveTicker} />
      <div className="space-y-8 md:space-y-10">
        <ArchaeologyDashboard activeTicker={activeTicker} />
        <StackStatus />
      </div>
    </div>
  );
}
