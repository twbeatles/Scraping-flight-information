"""Shared flight-result export helpers."""

from __future__ import annotations

import csv
from typing import Any, Iterable


EXPORT_HEADERS = [
    "항공사",
    "오는편 항공사",
    "가격",
    "혜택가",
    "혜택 정보",
    "가는편 출발",
    "가는편 도착",
    "경유",
    "오는편 출발",
    "오는편 도착",
    "오는편 경유",
    "출처",
    "가는편 가격",
    "오는편 가격",
]


def flight_export_headers() -> list[str]:
    return list(EXPORT_HEADERS)


def flight_to_export_row(flight: Any) -> list[Any]:
    return [
        getattr(flight, "airline", ""),
        getattr(flight, "return_airline", ""),
        getattr(flight, "price", 0),
        getattr(flight, "benefit_price", 0),
        getattr(flight, "benefit_label", ""),
        getattr(flight, "departure_time", ""),
        getattr(flight, "arrival_time", ""),
        getattr(flight, "stops", 0),
        getattr(flight, "return_departure_time", ""),
        getattr(flight, "return_arrival_time", ""),
        getattr(flight, "return_stops", 0),
        getattr(flight, "source", ""),
        getattr(flight, "outbound_price", 0),
        getattr(flight, "return_price", 0),
    ]


def flight_export_rows(flights: Iterable[Any]) -> list[list[Any]]:
    return [flight_to_export_row(flight) for flight in flights]


def export_flights_to_csv(filepath: str, flights: Iterable[Any]) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(flight_export_headers())
        writer.writerows(flight_export_rows(flights))


def export_flights_to_excel(filepath: str, flights: Iterable[Any], *, sheet_title: str = "검색 결과") -> None:
    import openpyxl
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    if ws is None:
        raise RuntimeError("worksheet initialization failed")
    ws.title = sheet_title
    ws.append(flight_export_headers())
    for row in flight_export_rows(flights):
        ws.append(row)

    for col_idx, col in enumerate(ws.columns, start=1):
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[get_column_letter(col_idx)].width = max_length + 2

    wb.save(filepath)
