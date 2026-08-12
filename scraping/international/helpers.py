"""International result helper functions."""

import re
from typing import Any, Dict, Iterable, Optional

from scraping.models import FlightResult


def _schedule_bounds(schedule: Optional[Dict[str, Any]]) -> tuple[str, str]:
    if not isinstance(schedule, dict):
        return "", ""

    segments = schedule.get("segments")
    if isinstance(segments, list) and segments:
        first = segments[0] if isinstance(segments[0], dict) else {}
        last = segments[-1] if isinstance(segments[-1], dict) else {}
        return _iso_timestamp_to_hhmm(_nested_get(first, "departure", "at")), _iso_timestamp_to_hhmm(
            _nested_get(last, "arrival", "at")
        )
    return "", ""


def _schedule_airline(schedule: Optional[Dict[str, Any]]) -> str:
    if not isinstance(schedule, dict):
        return ""

    carrier = schedule.get("carrier")
    if isinstance(carrier, dict) and carrier.get("name"):
        return str(carrier["name"])

    marketing = schedule.get("marketingCarriers")
    if isinstance(marketing, list):
        for item in marketing:
            if isinstance(item, dict) and item.get("name"):
                return str(item["name"])

    segments = schedule.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            marketing_carrier = segment.get("marketingCarrier")
            if isinstance(marketing_carrier, dict) and marketing_carrier.get("name"):
                return str(marketing_carrier["name"])
    return ""


def _browser_item_unique_key(item: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("airline", "") or ""),
            str(item.get("returnAirline", "") or ""),
            str(_coerce_int(item.get("price"))),
            str(item.get("depTime", "") or ""),
            str(item.get("arrTime", "") or ""),
            str(_coerce_int(item.get("stops"))),
            str(item.get("retDepTime", "") or ""),
            str(item.get("retArrTime", "") or ""),
            str(_coerce_int(item.get("retStops"))),
        ]
    )


def _result_unique_key(result: FlightResult) -> str:
    return "|".join(
        [
            result.airline,
            result.return_airline,
            str(result.price),
            result.departure_time,
            result.arrival_time,
            str(result.stops),
            result.return_departure_time,
            result.return_arrival_time,
            str(result.return_stops),
        ]
    )


def _iso_timestamp_to_hhmm(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) >= 16 and "T" in text:
        return text[11:16]
    return ""


def _iso_duration_to_text(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text.startswith("PT"):
        return ""

    hour_match = re.search(r"(\d+)H", text)
    minute_match = re.search(r"(\d+)M", text)
    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0
    if hours and minutes:
        return f"{hours:02d}시간 {minutes:02d}분"
    if hours:
        return f"{hours:02d}시간"
    if minutes:
        return f"{minutes:02d}분"
    return ""


def _nested_get(value: Dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _schedule_airports(schedule: Optional[Dict[str, Any]]) -> tuple[str, str]:
    """Return (departure_airport, arrival_airport) IATA codes from segments."""
    if not isinstance(schedule, dict):
        return "", ""
    segments = schedule.get("segments")
    if not isinstance(segments, list) or not segments:
        return "", ""
    first = segments[0] if isinstance(segments[0], dict) else {}
    last = segments[-1] if isinstance(segments[-1], dict) else {}
    dep = str(_nested_get(first, "departure", "airport", "code") or "").strip().upper()
    arr = str(_nested_get(last, "arrival", "airport", "code") or "").strip().upper()
    return dep, arr


def _format_free_baggage(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    allowance = value.get("allowance")
    unit = str(value.get("unit") or "").strip().upper()
    if allowance is None or allowance == "":
        return ""
    try:
        amount = int(allowance)
    except (TypeError, ValueError):
        text = str(allowance).strip()
        return text
    if amount <= 0:
        return ""
    if unit in {"WEIGHT_KG", "KG", "WEIGHT"}:
        return f"{amount}kg"
    if unit in {"QUANTITY", "PIECE", "PC", "PCS"}:
        return f"{amount}개"
    return str(amount)


def _schedule_baggage(schedule: Optional[Dict[str, Any]]) -> str:
    if not isinstance(schedule, dict):
        return ""
    direct = _format_free_baggage(schedule.get("freeBaggage"))
    if direct:
        return direct
    segments = schedule.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            label = _format_free_baggage(segment.get("freeBaggage"))
            if label:
                return label
    return ""


def _select_international_fare(item: Dict[str, Any]) -> Dict[str, Any]:
    base_price = _first_positive_int(
        item,
        ("adultPrice", "totalPrice", "totalFare", "price", "sellPrice", "salePrice"),
    )
    candidates: list[Dict[str, Any]] = []
    fares = item.get("fares")
    if isinstance(fares, list):
        for fare in fares:
            if not isinstance(fare, dict):
                continue
            fare_price = _first_positive_int(
                fare,
                ("adultPrice", "totalPrice", "totalFare", "price", "sellPrice", "salePrice"),
            )
            if fare_price <= 0:
                fare_price = base_price
            if fare_price <= 0:
                continue
            benefit_price, benefit_label = _extract_international_benefit(fare)
            promo_label = _promotion_label_from_fare(fare)
            if promo_label and not benefit_label:
                benefit_label = promo_label
            elif promo_label and promo_label not in benefit_label:
                benefit_label = f"{benefit_label} / {promo_label}" if benefit_label else promo_label
            candidates.append(
                {
                    "price": fare_price,
                    "benefit_price": benefit_price,
                    "benefit_label": benefit_label,
                    "avail": _coerce_int(fare.get("avail")),
                }
            )

    if candidates:
        selected = min(candidates, key=lambda value: value["price"])
    else:
        selected = {
            "price": base_price,
            "benefit_price": 0,
            "benefit_label": "",
            "avail": 0,
        }

    top_benefit_price, top_benefit_label = _extract_international_benefit(item)
    if selected["benefit_price"] <= 0 and top_benefit_price > 0:
        selected["benefit_price"] = top_benefit_price
    if not selected["benefit_label"] and top_benefit_label:
        selected["benefit_label"] = top_benefit_label
    if selected["benefit_price"] > 0 and not selected["benefit_label"]:
        selected["benefit_label"] = "혜택가"
    return selected


def _promotion_label_from_fare(fare: Dict[str, Any]) -> str:
    items = fare.get("items")
    if not isinstance(items, list):
        return ""
    labels: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        principle = item.get("promotionPrinciple")
        if isinstance(principle, dict):
            name = str(principle.get("promotionName") or "").strip()
            if name:
                labels.append(name)
    return " / ".join(labels[:2])


def _extract_international_benefit(container: Dict[str, Any]) -> tuple[int, str]:
    best_price = _first_positive_int(
        container,
        ("benefitPrice", "discountedPrice", "discountPrice", "paymentPrice", "finalPrice"),
    )
    label_parts = _benefit_label_parts(container)

    for key in (
        "benefits",
        "benefit",
        "promotions",
        "promotion",
        "discounts",
        "discount",
        "paymentBenefits",
        "paymentBenefit",
        "cardBenefits",
        "cardBenefit",
        "cardCashback",
        "paymentMethods",
    ):
        value = container.get(key)
        for node in _iter_benefit_nodes(value):
            node_price = _first_positive_int(
                node,
                ("discountedPrice", "benefitPrice", "discountPrice", "paymentPrice", "finalPrice", "amount"),
            )
            if node_price > 0 and (best_price <= 0 or node_price < best_price):
                best_price = node_price
            label_parts.extend(_benefit_label_parts(node))

    return best_price, _join_label_parts(label_parts)


def _first_positive_int(container: Dict[str, Any], keys: tuple[str, ...]) -> int:
    for key in keys:
        value = _coerce_int(container.get(key))
        if value > 0:
            return value
    return 0


def _iter_benefit_nodes(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested_key in ("cardCashback", "promotion", "benefit", "discount"):
            nested = value.get(nested_key)
            if isinstance(nested, dict):
                yield nested
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield from _iter_benefit_nodes(item)


def _benefit_label_parts(container: Dict[str, Any]) -> list[str]:
    parts: list[str] = []
    card_name = str(container.get("cardName", "") or "").strip()
    rate = container.get("rate")
    amount = _coerce_int(container.get("amount"))
    if card_name:
        if rate:
            parts.append(f"{card_name} {rate}% 캐시백 적용 시")
        elif amount > 0:
            parts.append(f"{card_name} {amount:,}원 캐시백 적용 시")
        else:
            parts.append(card_name)

    for key in (
        "benefitLabel",
        "promotionName",
        "promoName",
        "discountName",
        "paymentMethodName",
        "title",
        "name",
        "label",
        "description",
        "condition",
    ):
        value = str(container.get(key, "") or "").strip()
        if value:
            parts.append(value)
    return parts


def _join_label_parts(parts: Iterable[str]) -> str:
    seen: set[str] = set()
    labels: list[str] = []
    for part in parts:
        label = re.sub(r"\s+", " ", str(part or "")).strip(" /|,")
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= 3:
            break
    return " / ".join(labels)
