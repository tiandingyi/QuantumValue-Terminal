"""Fetch historical market price data for a ticker around a given date.

Strategy (priority order):
1. Static pre-seeded market-cap table for tickers where live feeds are blocked.
2. Full yfinance history fetch (once per ticker per process) as a fallback.

The static table stores total market capitalisation in USD at each fiscal
year-end date.  spot_price is then derived as market_cap / shares_outstanding
so the PE ratio formula (spot_price / eps) is consistent regardless of which
stock-split adjustment basis the SEC shares_outstanding figure uses.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static market-cap seed table
# ---------------------------------------------------------------------------
# Keys are fiscal-year period-end dates (ISO-8601) as reported in SEC filings.
# Values are total equity market capitalisation in USD.
#
# AAPL prices reflect the split-adjustment basis that matches
# WeightedAverageNumberOfDilutedSharesOutstanding for each period:
#   FY2007-2011 → pre-7:1-split  (~880M–936M shares, actual pre-split prices)
#   FY2012-2013 → post-7:1-split (~6.5B shares, price ÷ 7 of actual)
#   FY2014-2017 → post-7:1 actual (~5.25B–6.12B shares, actual post-7:1 prices)
#   FY2018-2019 → post-4:1-split (~18.6B–20B shares, price ÷ 4 of post-7:1)
#   FY2020+     → post-both-splits actual (~15B–17.5B shares)
#
# COST has never split (since FY2000), so all prices are actual.
_STATIC_MARKET_CAPS: dict[str, dict[str, float]] = {
    "AAPL": {
        "2007-09-29": 136_440_000_000,   # ~$153.47 × 889M
        "2008-09-27": 115_500_000_000,   # ~$128 × 902M
        "2009-09-26": 167_800_000_000,   # ~$185 × 907M
        "2010-09-25": 262_500_000_000,   # ~$284 × 925M
        "2011-09-24": 370_000_000_000,   # ~$395 × 937M
        "2012-09-29": 626_000_000_000,   # ~$95.4 × 6,617M (= $668 ÷ 7)
        "2013-09-28": 451_000_000_000,   # ~$69.1 × 6,522M (= $484 ÷ 7)
        "2014-09-27": 617_000_000_000,   # ~$100.75 × 6,122M
        "2015-09-26": 666_000_000_000,   # ~$115 × 5,793M
        "2016-09-24": 622_000_000_000,   # ~$113 × 5,500M
        "2017-09-30": 809_000_000_000,   # ~$154 × 5,252M
        "2018-09-29": 1_129_000_000_000, # ~$56.44 × 20,000M (= $225.74 ÷ 4)
        "2019-09-28": 1_018_000_000_000, # ~$54.74 × 18,596M (= $218.96 ÷ 4)
        "2020-09-26": 1_967_000_000_000, # ~$112.27 × 17,528M
        "2021-09-25": 2_459_000_000_000, # ~$145.85 × 16,865M
        "2022-09-24": 2_455_000_000_000, # ~$150.43 × 16,326M
        "2023-09-30": 2_707_000_000_000, # ~$171.21 × 15,813M
        "2024-09-28": 3_506_000_000_000, # ~$227.52 × 15,408M
        "2025-09-27": 3_398_000_000_000, # ~$226.51 × 15,005M
        "2025-12-27": 3_690_000_000_000, # FY26 Q1 close basis
        "2026-03-28": 3_430_000_000_000, # FY26 Q2 close basis
    },
    "COST": {
        "2008-08-31": 29_500_000_000,    # ~$66 × 444M
        "2009-08-30": 23_800_000_000,    # ~$54 × 440M
        "2010-08-29": 28_500_000_000,    # ~$64 × 446M
        "2011-08-28": 32_300_000_000,    # ~$73 × 443M
        "2012-09-02": 41_700_000_000,    # ~$95 × 439M
        "2013-09-01": 51_000_000_000,    # ~$116 × 441M
        "2014-08-31": 53_000_000_000,    # ~$120 × 442M
        "2015-08-30": 67_800_000_000,    # ~$153 × 443M
        "2016-08-28": 65_500_000_000,    # ~$148 × 442M
        "2017-09-03": 70_800_000_000,    # ~$161 × 441M
        "2018-09-02": 102_900_000_000,   # ~$233 × 441M
        "2019-09-01": 130_800_000_000,   # ~$295 × 443M
        "2020-08-30": 157_600_000_000,   # ~$355 × 444M
        "2021-08-29": 202_200_000_000,   # ~$455 × 444M
        "2022-08-28": 217_800_000_000,   # ~$490 × 445M
        "2023-09-03": 247_800_000_000,   # ~$558 × 444M
        "2024-09-01": 398_900_000_000,   # ~$897 × 445M
        "2025-08-31": 436_100_000_000,   # ~$980 × 445M
        "2025-11-23": 432_300_000_000,   # FY26 Q1 close basis
        "2026-02-15": 436_900_000_000,   # FY26 Q2 close basis
    },
}


def _lookup_static_market_cap(ticker: str, date_str: str) -> Optional[float]:
    """Return a pre-seeded market cap for *ticker* within ±7 calendar days of *date_str*.

    Returns None when the ticker is not in the static table or no entry falls
    within the search window.
    """
    table = _STATIC_MARKET_CAPS.get(ticker)
    if not table:
        return None
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return None

    best_cap: Optional[float] = None
    best_diff = float("inf")
    for offset in range(-7, 8):
        candidate = (target + timedelta(days=offset)).isoformat()
        if candidate in table:
            diff = abs(offset)
            if diff < best_diff:
                best_diff = diff
                best_cap = table[candidate]
    return best_cap


# Per-ticker full history: {ticker -> {date_iso: close_price}}
# None means the fetch already failed and should not be retried this session.
_history_cache: dict[str, Optional[dict[str, float]]] = {}


def _load_history(ticker: str) -> Optional[dict[str, float]]:
    """Fetch full daily price history for *ticker* (once per process lifetime).

    Returns a mapping of ISO date strings to adjusted closing prices, or None
    if the fetch fails.
    """
    if ticker in _history_cache:
        return _history_cache[ticker]

    logger.info("market_data: fetching full price history for %s via yfinance", ticker)
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="max", interval="1d", auto_adjust=True)
    except Exception as exc:
        logger.warning("market_data: yfinance history fetch failed for %s: %s", ticker, exc)
        _history_cache[ticker] = None
        return None

    if hist is None or (hasattr(hist, "empty") and hist.empty):
        logger.warning("market_data: empty history returned for %s", ticker)
        _history_cache[ticker] = None
        return None

    prices: dict[str, float] = {}
    for idx, row in hist.iterrows():
        try:
            if hasattr(idx, "date"):
                d_obj = idx.date()
            else:
                d_obj = date.fromisoformat(str(idx)[:10])
            close_val = row.get("Close") if hasattr(row, "get") else row["Close"]
            if close_val is not None and not pd.isna(close_val):
                prices[d_obj.isoformat()] = float(close_val)
        except Exception:
            continue

    logger.info("market_data: cached %d price points for %s", len(prices), ticker)
    _history_cache[ticker] = prices
    return prices


def fetch_price_at_date(ticker: str, date_str: str) -> Optional[float]:
    """Return the closing price for *ticker* on or nearest to *date_str*.

    *date_str* must be an ISO-8601 date string (YYYY-MM-DD).  Searches within
    a ±7 calendar-day window to account for weekends and market holidays.
    Returns None if no price data is available near the date.
    """
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        logger.warning("market_data: invalid date_str %r for ticker %s", date_str, ticker)
        return None

    prices = _load_history(ticker)
    if not prices:
        logger.warning("market_data: no price data available for %s on %s", ticker, date_str)
        return None

    best_price: Optional[float] = None
    best_diff = float("inf")
    for offset in range(-7, 8):
        candidate = (target + timedelta(days=offset)).isoformat()
        if candidate in prices:
            diff = abs(offset)
            if diff < best_diff:
                best_diff = diff
                best_price = prices[candidate]

    if best_price is None:
        logger.warning("market_data: no trading day within ±7d of %s for %s", date_str, ticker)
    else:
        logger.debug("market_data: price for %s on %s → %.4f (offset %+dd)", ticker, date_str, best_price, best_diff)

    return best_price


def fetch_market_data_for_period(
    ticker: str,
    period_end: Optional[str],
    shares_outstanding: Optional[float],
) -> dict[str, Optional[float]]:
    """Return a dict with spot_price and market_cap for a filing period.

    Checks the static market-cap table first; falls back to yfinance.
    Both values may be None if data is unavailable.
    """
    if not period_end:
        return {"spot_price": None, "market_cap": None}

    # 1. Static seed table (used when live feeds are blocked/unavailable).
    static_cap = _lookup_static_market_cap(ticker, period_end)
    if static_cap is not None and shares_outstanding not in (None, 0):
        spot_price = static_cap / float(shares_outstanding)
        logger.info(
            "market_data: static cap %.2fB for %s on %s → implied price %.4f",
            static_cap / 1e9,
            ticker,
            period_end,
            spot_price,
        )
        return {"spot_price": spot_price, "market_cap": static_cap}

    # 2. Live yfinance fallback.
    spot_price = fetch_price_at_date(ticker, period_end)
    market_cap: Optional[float] = None
    if spot_price is not None and shares_outstanding not in (None, 0):
        market_cap = spot_price * float(shares_outstanding)

    return {"spot_price": spot_price, "market_cap": market_cap}
