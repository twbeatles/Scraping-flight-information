"""Domestic extraction orchestration and result building."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from scraping.models import FlightResult
from scraping.domestic.api import clear_domestic_api_failure_after_success, extract_domestic_api_flights_data
from scraping.domestic.dom import extract_domestic_dom_flights_data
from scraping.domestic.helpers import _coerce_int, _combine_benefit_labels

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def extract_domestic_flights_data(scraper: "PlaywrightScraper") -> list:
    """Collect domestic flight items, preferring the paged API over DOM scraping."""

    items, metadata = extract_domestic_api_flights_data(scraper)
    if items:
        clear_domestic_api_failure_after_success(scraper)
        scraper._search_metrics.update(
            {
                "api_total_count": _coerce_int(metadata.get("total_count")),
                "fetched_pages": _coerce_int(metadata.get("fetched_pages")),
                "api_fetched_pages": _coerce_int(metadata.get("fetched_pages")),
                "api_page_cap": _coerce_int(metadata.get("page_cap")),
                "api_pages_truncated": bool(metadata.get("pages_truncated")),
                "api_total_pages_estimated": _coerce_int(metadata.get("total_pages_estimated")),
                "api_item_count": len(items),
            }
        )
        return items

    if not getattr(scraper, "_manual_reason", ""):
        scraper._manual_reason = "domestic_api_failed"
    dom_items = extract_domestic_dom_flights_data(scraper)
    if dom_items:
        clear_domestic_api_failure_after_success(scraper)
    return dom_items


def build_domestic_results(
    items: List[Dict[str, Any]],
    *,
    source: str = "Interpark (국내선)",
    extraction_source: str = "domestic_scroll",
    confidence: float = 0.75,
) -> List[FlightResult]:
    """Normalize raw domestic items into `FlightResult`s."""

    results: List[FlightResult] = []
    seen = set()

    for item in items or []:
        price = int(item.get("price", 0) or 0)
        dep_time = item.get("depTime", "") or ""
        arr_time = item.get("arrTime", "") or ""
        airline = item.get("airline", "Unknown") or "Unknown"
        stops = int(item.get("stops", 0) or 0)
        flight_number = str(item.get("flightNumber", "") or "")
        benefit_price = _coerce_int(item.get("benefitPrice"))
        benefit_label = str(item.get("benefitLabel", "") or "")

        if price <= 0 or not dep_time or not arr_time:
            continue

        key = "|".join(
            [
                str(item.get("key", "") or ""),
                airline,
                dep_time,
                arr_time,
                str(price),
                flight_number,
                str(benefit_price),
                benefit_label,
            ]
        )
        if key in seen:
            continue
        seen.add(key)

        results.append(
            FlightResult(
                airline=airline,
                price=price,
                departure_time=dep_time,
                arrival_time=arr_time,
                duration=str(item.get("duration", "") or ""),
                stops=stops,
                flight_number=flight_number,
                source=source,
                return_departure_time="",
                return_arrival_time="",
                return_stops=0,
                is_round_trip=False,
                benefit_price=benefit_price,
                benefit_label=benefit_label,
                departure_airport=str(item.get("depAirport", "") or "").upper(),
                arrival_airport=str(item.get("arrAirport", "") or "").upper(),
                seat_availability=_coerce_int(item.get("seatAvailability")),
                confidence=confidence,
                extraction_source=extraction_source,
            )
        )

    return results


def extract_domestic_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    """Convert scrolled domestic results into final results."""

    if not scraper.page:
        return []

    logger.info("🇰🇷 국내선 항공편 추출 시작...")
    try:
        extracted = scraper._extract_domestic_flights_data()
        results = build_domestic_results(
            extracted,
            source="Interpark (국내선)",
            extraction_source="domestic_api" if any(item.get("flightNumber") for item in extracted) else "domestic_scroll",
            confidence=0.9 if any(item.get("flightNumber") for item in extracted) else 0.75,
        )
        logger.info("🇰🇷 국내선 추출 완료: %s개", len(results))
        return results
    except Exception as exc:
        logger.error("Domestic extraction error: %s", exc, exc_info=True)
        return []
