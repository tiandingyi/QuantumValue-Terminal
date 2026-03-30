from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ENGINE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PYTHON_ENGINE_DIR))

from app.providers.us_provider import USProvider  # noqa: E402


def format_metric_line(label: str, metric) -> str:
    if metric.unit == "ratio":
        value = f"{metric.value:.2%}"
        unit = ""
    else:
        value = f"{metric.value:,.0f}"
        unit = f" {metric.unit}"

    filed_suffix = f", filed={metric.filed}" if metric.filed else ""
    return f"{label}: {value}{unit} (end={metric.end}{filed_suffix}, source={metric.source})"


def main() -> None:
    provider = USProvider()
    bundle = provider.fetch_company_data("NVDA")
    latest_assets = provider.extract_latest_metric(bundle.company_facts, "Assets")
    metrics = provider.extract_requested_financials(bundle.company_facts)

    print(f"Ticker: {bundle.company.ticker}")
    print(f"Entity Name: {bundle.company.name}")
    print(f"CIK: {bundle.company.cik}")
    print(f"Submissions Name: {bundle.submissions.get('name', 'unknown')}")
    print(
        "Latest Assets: "
        f"{latest_assets['val']} {latest_assets['unit']} "
        f"(end={latest_assets['end']}, filed={latest_assets.get('filed', 'n/a')})"
    )
    print(format_metric_line("FCF", metrics["fcf"]))
    print(format_metric_line("Net Income", metrics["net_income"]))
    print(format_metric_line("NOPAT", metrics["nopat"]))
    print(format_metric_line("Invested Capital", metrics["invested_capital"]))
    print(format_metric_line("Gross Margin", metrics["gross_margin"]))
    print(format_metric_line("EBIT", metrics["ebit"]))
    print(format_metric_line("Interest Expense", metrics["interest_expense"]))


if __name__ == "__main__":
    main()
