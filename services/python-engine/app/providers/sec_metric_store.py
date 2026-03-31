from __future__ import annotations

from typing import Any, Optional

from app.providers.sec_utils import is_annual_filing, parse_date, score_anchor_match


class CompanyFactsMetricStore:
    """Read and rank raw XBRL facts from the SEC company facts payload.

    This helper is intentionally state-light: it wraps one ``company_facts``
    payload and exposes a few selection strategies for the rest of the engine.
    """

    def __init__(self, company_facts: dict[str, Any]) -> None:
        """Store the SEC company facts document used for later lookups."""
        self._company_facts = company_facts

    def latest_metric(self, metric_name: str, taxonomy: str = "us-gaap") -> dict[str, Any]:
        """Return the latest reported fact for a single metric tag.

        Args:
            metric_name: XBRL tag name to inspect.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            dict[str, Any]: Latest fact entry enriched with its unit.

        Raises:
            ValueError: If no dated values exist for the requested tag.
        """
        candidates = self.collect_metric_candidates(metric_name, taxonomy=taxonomy)
        if not candidates:
            raise ValueError(f"Metric {taxonomy}:{metric_name} does not contain any dated values.")

        candidates.sort(
            key=lambda item: (
                parse_date(item.get("end")),
                parse_date(item.get("filed")),
            ),
            reverse=True,
        )
        return candidates[0]

    def latest_metric_from_candidates(
        self,
        metric_names: list[str],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        """Try a list of fallback tags and return the first metric that has data.

        Args:
            metric_names: Ordered fallback tag names.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            tuple[str, dict[str, Any]]: The chosen tag name and matching fact.
        """
        for metric_name in metric_names:
            try:
                return metric_name, self.latest_metric(metric_name, taxonomy=taxonomy)
            except ValueError:
                continue

        raise ValueError(
            f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
        )

    def anchor_metric(
        self,
        metric_names: list[str],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        """Choose the best anchor fact for period-aligned downstream calculations.

        The anchor is usually an annual revenue or net-income fact and is used
        to align all later lookups onto the same reporting period.
        """
        best_match: Optional[tuple[str, dict[str, Any]]] = None
        for metric_name in metric_names:
            candidates = self.collect_metric_candidates(metric_name, taxonomy=taxonomy)
            if not candidates:
                continue

            candidates.sort(
                key=lambda item: (
                    is_annual_filing(item),
                    parse_date(item.get("end")),
                    parse_date(item.get("filed")),
                ),
                reverse=True,
            )
            candidate = candidates[0]
            if best_match is None:
                best_match = (metric_name, candidate)
                continue

            if (
                is_annual_filing(candidate),
                parse_date(candidate.get("end")),
                parse_date(candidate.get("filed")),
            ) > (
                is_annual_filing(best_match[1]),
                parse_date(best_match[1].get("end")),
                parse_date(best_match[1].get("filed")),
            ):
                best_match = (metric_name, candidate)

        if best_match is None:
            raise ValueError(
                f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
            )
        return best_match

    def metric_for_anchor_period(
        self,
        metric_names: list[str],
        anchor: dict[str, Any],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        """Pick the fact that best matches the anchor filing period for a metric family.

        Args:
            metric_names: Ordered fallback tag names for the same concept.
            anchor: Previously selected fact used to define the target period.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            tuple[str, dict[str, Any]]: The chosen tag name and aligned fact.
        """
        anchor_end = anchor.get("end")
        anchor_form = anchor.get("form")
        anchor_fp = anchor.get("fp")
        anchor_fy = anchor.get("fy")

        best_fallback: Optional[tuple[str, dict[str, Any]]] = None
        for metric_name in metric_names:
            candidates = self.collect_metric_candidates(metric_name, taxonomy=taxonomy)
            if not candidates:
                continue

            # Prefer facts reported for the same filing period so derived ratios
            # are not mixing annual and quarterly values.
            exact_matches = [
                item
                for item in candidates
                if item.get("end") == anchor_end
                and (anchor_form is None or item.get("form") == anchor_form)
                and (anchor_fp is None or item.get("fp") == anchor_fp)
            ]
            if exact_matches:
                exact_matches.sort(
                    key=lambda item: (parse_date(item.get("filed")), parse_date(item.get("end"))),
                    reverse=True,
                )
                return metric_name, exact_matches[0]

            same_end_matches = [item for item in candidates if item.get("end") == anchor_end]
            if same_end_matches:
                same_end_matches.sort(
                    key=lambda item: (
                        score_anchor_match(
                            item,
                            anchor_fy=anchor_fy,
                            anchor_fp=anchor_fp,
                            anchor_form=anchor_form,
                        ),
                        parse_date(item.get("filed")),
                    ),
                    reverse=True,
                )
                return metric_name, same_end_matches[0]

            ranked_candidates = sorted(
                candidates,
                key=lambda item: (
                    score_anchor_match(
                        item,
                        anchor_fy=anchor_fy,
                        anchor_fp=anchor_fp,
                        anchor_form=anchor_form,
                    ),
                    parse_date(item.get("end")),
                    parse_date(item.get("filed")),
                ),
                reverse=True,
            )
            candidate = (metric_name, ranked_candidates[0])
            if best_fallback is None or ranked_candidates[0] != best_fallback[1]:
                best_fallback = candidate

        if best_fallback is not None:
            return best_fallback

        raise ValueError(
            f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
        )

    def collect_metric_candidates(
        self,
        metric_name: str,
        taxonomy: str = "us-gaap",
    ) -> list[dict[str, Any]]:
        """Flatten one XBRL metric node into comparable fact entries across units.

        Args:
            metric_name: XBRL tag name to collect.
            taxonomy: XBRL taxonomy namespace. Defaults to ``us-gaap``.

        Returns:
            list[dict[str, Any]]: All usable facts for the requested tag.
        """
        taxonomy_facts = self._company_facts.get("facts", {}).get(taxonomy, {})
        metric_node = taxonomy_facts.get(metric_name)
        if not metric_node:
            return []

        candidates: list[dict[str, Any]] = []
        for unit_name, entries in metric_node.get("units", {}).items():
            for entry in entries:
                if "val" not in entry or entry.get("val") is None or "end" not in entry:
                    continue
                candidate = dict(entry)
                candidate["unit"] = unit_name
                candidates.append(candidate)
        return candidates
