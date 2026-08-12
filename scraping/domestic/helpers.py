"""Domestic result helper functions."""

from __future__ import annotations

import heapq
from typing import Any, Dict, List, Tuple

import scraping.interpark as scraper_config
from scraping.models import FlightResult


def combine_domestic_round_trip(
    outbound_flights: List[Dict[str, Any]],
    return_flights: List[Dict[str, Any]],
    max_results: int,
) -> List[FlightResult]:
    """Create the cheapest domestic round-trip combinations."""

    outbound_flights = [
        item
        for item in outbound_flights
        if item.get("price", 0) > 0 and item.get("depTime") and item.get("arrTime")
    ]
    return_flights = [
        item
        for item in return_flights
        if item.get("price", 0) > 0 and item.get("depTime") and item.get("arrTime")
    ]
    if not outbound_flights or not return_flights:
        return []

    outbound_flights.sort(key=lambda item: item["price"])
    return_flights.sort(key=lambda item: item["price"])
    top_outbound = outbound_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]
    top_return = return_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]

    max_keep = (
        max_results
        if isinstance(max_results, int) and max_results > 0
        else len(top_outbound) * len(top_return)
    )
    max_heap: list[tuple[int, int, FlightResult]] = []
    seen = set()
    seq = 0

    for outbound in top_outbound:
        for returning in top_return:
            total_price = outbound["price"] + returning["price"]
            dedup_key = (
                str(outbound.get("key", "") or ""),
                str(returning.get("key", "") or ""),
                outbound["airline"],
                returning["airline"],
                total_price,
                outbound["depTime"],
                outbound.get("arrTime", ""),
                returning["depTime"],
                returning.get("arrTime", ""),
                outbound.get("flightNumber", ""),
                returning.get("flightNumber", ""),
                _coerce_int(outbound.get("benefitPrice")),
                _coerce_int(returning.get("benefitPrice")),
                str(outbound.get("benefitLabel", "") or ""),
                str(returning.get("benefitLabel", "") or ""),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            seq += 1

            outbound_seats = _coerce_int(outbound.get("seatAvailability"))
            return_seats = _coerce_int(returning.get("seatAvailability"))
            seat_availability = 0
            if outbound_seats > 0 and return_seats > 0:
                seat_availability = min(outbound_seats, return_seats)
            elif outbound_seats > 0:
                seat_availability = outbound_seats
            elif return_seats > 0:
                seat_availability = return_seats

            flight = FlightResult(
                airline=outbound["airline"],
                price=total_price,
                departure_time=outbound["depTime"],
                arrival_time=outbound["arrTime"],
                duration=str(outbound.get("duration", "") or ""),
                stops=outbound["stops"],
                flight_number=str(outbound.get("flightNumber", "") or ""),
                source="Interpark (국내선)",
                return_departure_time=returning["depTime"],
                return_arrival_time=returning["arrTime"],
                return_duration=str(returning.get("duration", "") or ""),
                return_stops=returning["stops"],
                is_round_trip=True,
                outbound_price=outbound["price"],
                return_price=returning["price"],
                return_airline=returning["airline"],
                benefit_price=_coerce_int(outbound.get("benefitPrice")) + _coerce_int(returning.get("benefitPrice")),
                benefit_label=_combine_benefit_labels(outbound, returning),
                departure_airport=str(outbound.get("depAirport", "") or "").upper(),
                arrival_airport=str(outbound.get("arrAirport", "") or "").upper(),
                return_departure_airport=str(returning.get("depAirport", "") or "").upper(),
                return_arrival_airport=str(returning.get("arrAirport", "") or "").upper(),
                seat_availability=seat_availability,
                confidence=0.8,
                extraction_source="domestic_combined",
            )

            entry = (-total_price, -seq, flight)
            if len(max_heap) < max_keep:
                heapq.heappush(max_heap, entry)
                continue

            worst_price = -max_heap[0][0]
            worst_seq = -max_heap[0][1]
            if (total_price, seq) < (worst_price, worst_seq):
                heapq.heapreplace(max_heap, entry)

    ranked = sorted(max_heap, key=lambda item: (-item[0], -item[1]))
    return [item[2] for item in ranked]


def _iso_timestamp_to_hhmm(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) >= 16 and "T" in text:
        return text[11:16]
    return ""


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _combine_benefit_labels(outbound: Dict[str, Any], returning: Dict[str, Any]) -> str:
    parts: list[str] = []
    outbound_price = _coerce_int(outbound.get("benefitPrice"))
    return_price = _coerce_int(returning.get("benefitPrice"))
    outbound_label = str(outbound.get("benefitLabel", "") or "").strip()
    return_label = str(returning.get("benefitLabel", "") or "").strip()

    if outbound_price > 0:
        label = outbound_label or "혜택가"
        parts.append(f"가는편 {label}: {outbound_price:,}원")
    if return_price > 0:
        label = return_label or "혜택가"
        parts.append(f"오는편 {label}: {return_price:,}원")
    return " | ".join(parts)
