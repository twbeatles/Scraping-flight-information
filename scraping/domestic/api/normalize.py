"""Domestic API item normalization (SRP: payload -> record mapping only)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from scraping.domestic.helpers import _coerce_int, _iso_timestamp_to_hhmm
from scraping.interpark.contract.carriers import DOMESTIC_CARRIER_CODE_TO_NAME


# Backward-compatible alias for existing imports/tests.
DOMESTIC_CARRIER_NAMES = DOMESTIC_CARRIER_CODE_TO_NAME


def _collect_result_items(
    payload: Dict[str, Any],
    buckets: tuple[str, ...],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for bucket in buckets:
        value = payload.get(bucket)
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def _normalize_domestic_api_item(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}

    schedule = item.get("schedule")
    if not isinstance(schedule, dict):
        return {}

    dep_time = _iso_timestamp_to_hhmm(schedule.get("departureAt"))
    arr_time = _iso_timestamp_to_hhmm(schedule.get("arrivalAt"))
    if not dep_time or not arr_time:
        return {}

    fares = item.get("fares")
    if not isinstance(fares, list) or not fares:
        return {}

    best_price = 0
    best_benefit_price = 0
    best_benefit_label = ""
    for fare in fares:
        if not isinstance(fare, dict):
            continue
        total_price = _coerce_int(fare.get("totalPrice"))
        if total_price <= 0:
            continue
        benefit_price, benefit_label = _extract_domestic_benefit(fare)
        if best_price == 0 or total_price < best_price:
            best_price = total_price
            best_benefit_price = benefit_price
            best_benefit_label = benefit_label

    if best_price <= 0:
        return {}

    carrier_code = str(schedule.get("marketingCarrier", "") or "").upper()
    airline = DOMESTIC_CARRIER_CODE_TO_NAME.get(carrier_code, carrier_code or "Unknown")
    flight_number = str(schedule.get("flightNumber", "") or "")
    key = str(item.get("key") or item.get("id") or f"{carrier_code}_{dep_time}_{arr_time}_{best_price}")
    dep_airport = _domestic_airport_code(
        schedule,
        ("departureAirport", "originAirport", "departureAirportCode", "origin", "departure"),
        nested_keys=(("departure", "airport", "code"), ("departure", "code")),
    )
    arr_airport = _domestic_airport_code(
        schedule,
        ("arrivalAirport", "destinationAirport", "arrivalAirportCode", "destination", "arrival"),
        nested_keys=(("arrival", "airport", "code"), ("arrival", "code")),
    )

    return {
        "key": key,
        "airline": airline,
        "price": best_price,
        "benefitPrice": best_benefit_price,
        "benefitLabel": best_benefit_label,
        "depTime": dep_time,
        "arrTime": arr_time,
        "stops": 0,
        "flightNumber": flight_number,
        "seatAvailability": _coerce_int(item.get("seatAvailability")),
        "discountType": str(item.get("discountType", "") or ""),
        "depAirport": dep_airport,
        "arrAirport": arr_airport,
        "duration": str(schedule.get("duration") or schedule.get("flightTime") or ""),
    }


def _domestic_airport_code(
    schedule: Dict[str, Any],
    flat_keys: tuple[str, ...],
    *,
    nested_keys: tuple[tuple[str, ...], ...] = (),
) -> str:
    for key in flat_keys:
        value = schedule.get(key)
        if isinstance(value, dict):
            code = str(value.get("code") or value.get("airportCode") or "").strip().upper()
        else:
            code = str(value or "").strip().upper()
        if len(code) == 3 and code.isalpha():
            return code
    for path in nested_keys:
        current: Any = schedule
        for part in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        code = str(current or "").strip().upper()
        if len(code) == 3 and code.isalpha():
            return code
    return ""


def _extract_domestic_benefit(fare: Dict[str, Any]) -> Tuple[int, str]:
    benefits = fare.get("benefits")
    if not isinstance(benefits, list):
        return 0, ""

    best_price = 0
    best_label = ""
    for benefit in benefits:
        if not isinstance(benefit, dict):
            continue
        discounted_price = _coerce_int(benefit.get("discountedPrice"))
        if discounted_price <= 0:
            continue

        cashback = benefit.get("cardCashback")
        if isinstance(cashback, dict):
            card_name = str(cashback.get("cardName", "") or "").strip()
            rate = cashback.get("rate")
            amount = _coerce_int(cashback.get("amount"))
            if rate:
                label = f"{card_name} {rate}% 캐시백 적용 시".strip()
            elif amount > 0:
                label = f"{card_name} {amount:,}원 캐시백 적용 시".strip()
            else:
                label = f"{card_name} 혜택가".strip()
        else:
            label = "혜택가"

        if best_price == 0 or discounted_price < best_price:
            best_price = discounted_price
            best_label = label

    return best_price, best_label
