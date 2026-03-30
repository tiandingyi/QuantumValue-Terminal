from __future__ import annotations

import time
from typing import Callable, Optional

import requests

from app.providers.sec_constants import (
    DEFAULT_RATE_LIMIT_DELAY,
    SEC_BASE_URL,
    SEC_TICKER_MAP_URL,
    SEC_USER_AGENT,
)
from app.providers.sec_financials import extract_requested_financials
from app.providers.sec_metric_store import CompanyFactsMetricStore
from app.providers.sec_types import CompanyDataBundle, CompanyLookup, DerivedMetric
from app.providers.sec_utils import normalize_ticker, pad_cik


class USProvider:
    """Facade for SEC EDGAR access used by the FastAPI engine and manual scripts.

    The provider owns outbound HTTP behavior such as fair-access throttling,
    SEC-compliant headers, ticker-to-CIK resolution, and raw payload retrieval.
    It delegates company-facts parsing and derived metric construction to
    smaller helper modules so the public API stays simple.
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        request_delay: float = DEFAULT_RATE_LIMIT_DELAY,
        timeout: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a provider instance.

        Args:
            session: Optional requests session for connection reuse or testing.
            request_delay: Minimum delay between SEC requests in seconds.
            timeout: Per-request timeout in seconds.
            sleep_fn: Injectable sleep function used by the throttle.
            clock_fn: Injectable monotonic clock used by the throttle.
        """
        self._session = session or requests.Session()
        self._request_delay = request_delay
        self._timeout = timeout
        self._sleep = sleep_fn
        self._clock = clock_fn
        self._last_request_at: Optional[float] = None
        self._ticker_cache: Optional[dict[str, CompanyLookup]] = None

    def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
        """Resolve a ticker and fetch both SEC submissions and company facts payloads.

        Args:
            ticker: User-supplied stock ticker such as ``AAPL`` or ``nvda``.

        Returns:
            CompanyDataBundle: Combined identity, submissions, and company facts.

        Raises:
            ValueError: If the ticker cannot be resolved in the SEC mapping file.
            requests.RequestException: If the SEC request fails.
        """
        company = self.resolve_ticker(ticker)
        submissions = self.get_submissions(company.cik)
        company_facts = self.get_company_facts(company.cik)
        return CompanyDataBundle(company=company, submissions=submissions, company_facts=company_facts)

    def resolve_ticker(self, ticker: str) -> CompanyLookup:
        """Map a case-insensitive stock ticker to the padded SEC CIK and company name.

        Args:
            ticker: User-supplied stock ticker.

        Returns:
            CompanyLookup: Normalized ticker, 10-digit CIK, and SEC company title.

        Raises:
            ValueError: If the ticker is empty or missing from SEC metadata.
        """
        normalized_ticker = normalize_ticker(ticker)
        ticker_map = self._load_ticker_map()
        company = ticker_map.get(normalized_ticker)
        if company is None:
            raise ValueError(f"Ticker {normalized_ticker} was not found in SEC company_tickers.json.")
        return company

    def get_submissions(self, cik: str) -> dict:
        """Fetch the raw SEC submissions document for a single issuer.

        Args:
            cik: Raw or padded SEC CIK.

        Returns:
            dict: Decoded JSON payload from ``/submissions/CIK{cik}.json``.
        """
        return self._get_json(f"{SEC_BASE_URL}/submissions/CIK{pad_cik(cik)}.json")

    def get_company_facts(self, cik: str) -> dict:
        """Fetch the raw SEC XBRL company facts document for a single issuer.

        Args:
            cik: Raw or padded SEC CIK.

        Returns:
            dict: Decoded JSON payload from ``/api/xbrl/companyfacts/CIK{cik}.json``.
        """
        return self._get_json(f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{pad_cik(cik)}.json")

    def extract_latest_metric(
        self,
        company_facts: dict,
        metric_name: str,
        taxonomy: str = "us-gaap",
    ) -> dict:
        """Return the most recent fact available for one XBRL metric tag.

        Args:
            company_facts: Raw SEC company facts payload.
            metric_name: XBRL tag name such as ``Assets`` or ``NetIncomeLoss``.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            dict: The best matching fact entry enriched with its unit.
        """
        return CompanyFactsMetricStore(company_facts).latest_metric(metric_name, taxonomy=taxonomy)

    def extract_latest_metric_from_candidates(
        self,
        company_facts: dict,
        metric_names: list[str],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict]:
        """Try fallback metric tags in order and return the first usable fact.

        Args:
            company_facts: Raw SEC company facts payload.
            metric_names: Ordered fallback list of XBRL tag names.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            tuple[str, dict]: The selected tag name and its fact payload.
        """
        return CompanyFactsMetricStore(company_facts).latest_metric_from_candidates(metric_names, taxonomy=taxonomy)

    def extract_requested_financials(self, company_facts: dict) -> dict[str, DerivedMetric]:
        """Build the derived metrics needed by the SEC validation script.

        Args:
            company_facts: Raw SEC company facts payload.

        Returns:
            dict[str, DerivedMetric]: Normalized metrics keyed by internal names
            such as ``fcf`` and ``gross_margin``.
        """
        return extract_requested_financials(company_facts)

    def _load_ticker_map(self) -> dict[str, CompanyLookup]:
        """Cache the SEC ticker mapping file so repeated lookups avoid extra network calls."""
        if self._ticker_cache is not None:
            return self._ticker_cache

        payload = self._get_json(SEC_TICKER_MAP_URL)
        ticker_map: dict[str, CompanyLookup] = {}
        for item in payload.values():
            ticker = normalize_ticker(item["ticker"])
            ticker_map[ticker] = CompanyLookup(
                ticker=ticker,
                cik=pad_cik(item["cik_str"]),
                name=item["title"],
            )

        self._ticker_cache = ticker_map
        return ticker_map

    def _get_json(self, url: str) -> dict:
        """Send one SEC request with the required headers and decode the JSON payload.

        Args:
            url: Fully qualified SEC endpoint URL.

        Returns:
            dict: Decoded JSON response body.

        Raises:
            requests.RequestException: If the SEC request fails.
        """
        self._throttle()
        response = self._session.get(
            url,
            headers={
                "User-Agent": SEC_USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        self._last_request_at = self._clock()
        return response.json()

    def _throttle(self) -> None:
        """Keep the single-threaded request rate under the SEC fair-access threshold."""
        if self._last_request_at is None:
            return

        elapsed = self._clock() - self._last_request_at
        remaining = self._request_delay - elapsed
        if remaining > 0:
            self._sleep(remaining)


__all__ = [
    "CompanyDataBundle",
    "CompanyLookup",
    "DEFAULT_RATE_LIMIT_DELAY",
    "DerivedMetric",
    "SEC_BASE_URL",
    "SEC_TICKER_MAP_URL",
    "SEC_USER_AGENT",
    "USProvider",
    "normalize_ticker",
    "pad_cik",
]
