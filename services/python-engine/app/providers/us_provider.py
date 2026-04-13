from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from email.utils import parsedate_to_datetime

import requests

from app.models.financial_metric import FinancialMetric
from app.parsers.financial_metric_parser import parse_financial_metric
from app.providers.sec_constants import (
    DEFAULT_BACKOFF_BASE_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_DELAY,
    SEC_BASE_URL,
    SEC_TICKER_MAP_URL,
    SEC_USER_AGENT,
)
from app.providers.sec_financials import extract_requested_financials
from app.providers.sec_metric_store import CompanyFactsMetricStore
from app.providers.sec_types import CompanyDataBundle, CompanyLookup, DerivedMetric
from app.providers.sec_utils import normalize_ticker, pad_cik


logger = logging.getLogger(__name__)


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
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_delay: float = DEFAULT_BACKOFF_BASE_DELAY,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a provider instance.

        Args:
            session: Optional requests session for connection reuse or testing.
            request_delay: Minimum delay between SEC requests in seconds.
            timeout: Per-request timeout in seconds.
            max_retries: Maximum retry attempts for 429 responses.
            backoff_base_delay: Base delay used for bounded exponential backoff.
            sleep_fn: Injectable sleep function used by the throttle.
            clock_fn: Injectable monotonic clock used by the throttle.
        """
        self._session = session or requests.Session()
        self._request_delay = request_delay
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base_delay = backoff_base_delay
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

    def parse_financial_metric(
        self,
        company_facts: dict,
        *,
        ticker: Optional[str] = None,
        cik: Optional[str] = None,
    ) -> FinancialMetric:
        """Parse raw SEC company facts into the standardized FinancialMetric model."""
        return parse_financial_metric(company_facts, ticker=ticker, cik=cik)

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
        response = self._request_with_resilience(url)
        return response.json()

    def _throttle(self) -> None:
        """Keep the single-threaded request rate under the SEC fair-access threshold."""
        if self._last_request_at is None:
            return

        elapsed = self._clock() - self._last_request_at
        remaining = self._request_delay - elapsed
        if remaining > 0:
            self._sleep(remaining)

    def _request_with_resilience(self, url: str) -> requests.Response:
        """Apply the shared SEC request policy: throttle first, then bounded retry on 429."""
        attempt = 0

        while attempt <= self._max_retries:
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
            self._last_request_at = self._clock()

            if response.status_code != 429:
                response.raise_for_status()
                return response

            if attempt == self._max_retries:
                response.raise_for_status()

            retry_delay = self._resolve_retry_delay(response, attempt)
            logger.warning(
                "SEC responded with 429 for %s. Retrying in %.2fs (attempt %d/%d).",
                url,
                retry_delay,
                attempt + 1,
                self._max_retries + 1,
            )
            self._sleep(retry_delay)
            attempt += 1

        raise requests.HTTPError("SEC request retry loop exited unexpectedly.")

    def _resolve_retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Prefer SEC-provided Retry-After values before falling back to exponential backoff."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            parsed_retry = _parse_retry_after_seconds(retry_after)
            if parsed_retry is not None and parsed_retry > 0:
                return parsed_retry

        return self._backoff_base_delay * (2**attempt)


def _parse_retry_after_seconds(
    retry_after: str,
) -> Optional[float]:
    try:
        return float(retry_after)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError, IndexError):
        return None

    now = datetime.now(timezone.utc)
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max((retry_at - now).total_seconds(), 0.0)


__all__ = [
    "CompanyDataBundle",
    "CompanyLookup",
    "DEFAULT_BACKOFF_BASE_DELAY",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RATE_LIMIT_DELAY",
    "DerivedMetric",
    "FinancialMetric",
    "SEC_BASE_URL",
    "SEC_TICKER_MAP_URL",
    "SEC_USER_AGENT",
    "USProvider",
    "normalize_ticker",
    "pad_cik",
]
