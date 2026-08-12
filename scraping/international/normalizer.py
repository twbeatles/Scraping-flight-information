"""International result normalization helpers."""

from typing import Any, Dict, Iterable, List, Optional

from scraping.models import FlightResult
from scraping.international.helpers import (
    _coerce_int,
    _iso_duration_to_text,
    _schedule_airline,
    _schedule_airports,
    _schedule_baggage,
    _schedule_bounds,
    _select_international_fare,
)


def _normalize_international_api_item(item: Dict[str, Any]) -> Optional[FlightResult]:
    schedules = item.get("schedules")
    if not isinstance(schedules, list) or not schedules:
        return None

    fare_summary = _select_international_fare(item)
    price = fare_summary["price"]
    if price <= 0:
        return None

    outbound = schedules[0] if isinstance(schedules[0], dict) else None
    inbound = schedules[1] if len(schedules) > 1 and isinstance(schedules[1], dict) else None
    if outbound is None:
        return None

    dep_time, arr_time = _schedule_bounds(outbound)
    if not dep_time or not arr_time:
        return None

    airline = _schedule_airline(outbound) or "Unknown"
    is_round_trip = inbound is not None
    return_dep_time, return_arr_time = _schedule_bounds(inbound) if inbound else ("", "")
    return_airline = _schedule_airline(inbound) if inbound else ""
    if is_round_trip and not return_airline:
        return_airline = airline

    dep_airport, arr_airport = _schedule_airports(outbound)
    ret_dep_airport, ret_arr_airport = _schedule_airports(inbound) if inbound else ("", "")

    return FlightResult(
        airline=airline,
        return_airline=return_airline,
        price=price,
        departure_time=dep_time,
        arrival_time=arr_time,
        duration=_iso_duration_to_text(outbound.get("totalFlightTime")),
        stops=_coerce_int(outbound.get("stop")),
        source="Interpark (API)",
        return_departure_time=return_dep_time,
        return_arrival_time=return_arr_time,
        return_duration=_iso_duration_to_text(inbound.get("totalFlightTime")) if inbound else "",
        return_stops=_coerce_int(inbound.get("stop")) if inbound else 0,
        is_round_trip=is_round_trip,
        benefit_price=fare_summary["benefit_price"],
        benefit_label=fare_summary["benefit_label"],
        departure_airport=dep_airport,
        arrival_airport=arr_airport,
        return_departure_airport=ret_dep_airport,
        return_arrival_airport=ret_arr_airport,
        baggage=_schedule_baggage(outbound),
        return_baggage=_schedule_baggage(inbound) if inbound else "",
        seat_availability=_coerce_int(fare_summary.get("avail")),
        arrival_day_offset=_coerce_int(outbound.get("addDay")),
        return_arrival_day_offset=_coerce_int(inbound.get("addDay")) if inbound else 0,
        recommendation_tag=str(item.get("recommendationTag") or "").strip(),
        confidence=0.98,
        extraction_source="international_api",
    )


def _build_international_results(items: Iterable[Dict[str, Any]]) -> List[FlightResult]:
    results: List[FlightResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        airline = str(item.get("airline", "Unknown") or "Unknown")
        is_round_trip = bool(item.get("isRoundTrip", False))
        return_airline = str(item.get("returnAirline", "") or "")
        if is_round_trip and not return_airline:
            return_airline = airline
        price = _coerce_int(item.get("price"))
        departure_time = str(item.get("depTime", "") or "")
        arrival_time = str(item.get("arrTime", "") or "")
        if price <= 0 or not departure_time or not arrival_time:
            continue
        results.append(
            FlightResult(
                airline=airline,
                return_airline=return_airline,
                price=price,
                departure_time=departure_time,
                arrival_time=arrival_time,
                stops=_coerce_int(item.get("stops")),
                source="Interpark (Auto)",
                return_departure_time=str(item.get("retDepTime", "") or ""),
                return_arrival_time=str(item.get("retArrTime", "") or ""),
                return_stops=_coerce_int(item.get("retStops")),
                is_round_trip=is_round_trip,
                benefit_price=_coerce_int(item.get("benefitPrice")),
                benefit_label=str(item.get("benefitLabel", "") or ""),
                confidence=float(item.get("confidence", 0.9) or 0.9),
                extraction_source=str(
                    item.get("extraction_source", "international_primary") or "international_primary"
                ),
            )
        )
    return results
