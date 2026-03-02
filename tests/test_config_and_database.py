import os
from datetime import datetime, timedelta
from pathlib import Path

from config import PreferenceManager
from database import FlightDatabase
from scraper_v2 import FlightResult


def test_default_max_results_is_1000(tmp_path: Path):
    pref_path = tmp_path / "prefs.json"
    prefs = PreferenceManager(filepath=str(pref_path))
    assert prefs.get_max_results() == 1000


def test_default_alert_auto_check_is_disabled(tmp_path: Path):
    pref_path = tmp_path / "prefs.json"
    prefs = PreferenceManager(filepath=str(pref_path))
    cfg = prefs.get_alert_auto_check()
    assert cfg["enabled"] is False
    assert cfg["interval_min"] == 30


def test_last_search_cache_limit_is_1000(tmp_path: Path):
    db_path = tmp_path / "flight_data.db"
    db = FlightDatabase(db_path=str(db_path))

    search_params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": "20260301",
        "ret": "20260305",
        "adults": 1,
        "cabin_class": "ECONOMY",
    }

    results = [
        FlightResult(
            airline=f"TestAir{i}",
            price=100000 + i,
            departure_time="10:00",
            arrival_time="12:00",
        )
        for i in range(1205)
    ]

    db.save_last_search_results(search_params, results)
    _, restored_results, _, _ = db.get_last_search_results()

    assert len(restored_results) == 1000


def test_last_search_metadata_fields_are_persisted(tmp_path: Path):
    db_path = tmp_path / "flight_data.db"
    db = FlightDatabase(db_path=str(db_path))

    search_params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": "20260301",
        "ret": "20260305",
        "adults": 1,
        "cabin_class": "BUSINESS",
    }
    results = [
        FlightResult(
            airline="MetaAir",
            price=222000,
            departure_time="10:00",
            arrival_time="12:00",
            confidence=0.88,
            extraction_source="international_primary",
        )
    ]
    db.save_last_search_results(search_params, results)
    _, restored, _, _ = db.get_last_search_results()

    assert len(restored) == 1
    assert restored[0].confidence == 0.88
    assert restored[0].extraction_source == "international_primary"


def test_close_all_connections_allows_db_file_removal(tmp_path: Path):
    db_path = tmp_path / "flight_data.db"
    db = FlightDatabase(db_path=str(db_path))
    db.get_stats()
    db.close_all_connections()
    os.remove(db_path)
    assert not db_path.exists()


def test_favorite_dedup_distinguishes_different_return_legs(tmp_path: Path):
    db = FlightDatabase(db_path=str(tmp_path / "flight_data.db"))

    base = {
        "airline": "TestAir",
        "price": 250000,
        "origin": "ICN",
        "destination": "NRT",
        "departure_date": "20260320",
        "return_date": "20260324",
        "departure_time": "09:00",
        "arrival_time": "11:00",
        "stops": 0,
        "return_airline": "TestAir",
        "return_departure_time": "15:00",
        "return_arrival_time": "17:00",
        "return_stops": 0,
        "is_round_trip": True,
        "outbound_price": 120000,
        "return_price": 130000,
    }
    variant = dict(base)
    variant["return_departure_time"] = "19:00"
    variant["return_arrival_time"] = "21:00"

    assert db.is_favorite_by_entry(base) is False
    db.add_favorite(base, {"origin": "ICN"})
    assert db.is_favorite_by_entry(base) is True
    assert db.is_favorite_by_entry(variant) is False

    db.add_favorite(variant, {"origin": "ICN"})
    favorites = db.get_favorites()
    assert len(favorites) == 2


def test_cleanup_old_data_removes_stale_telemetry_rows(tmp_path: Path):
    db = FlightDatabase(db_path=str(tmp_path / "flight_data.db"))

    old_time = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
    recent_time = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")

    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO telemetry_events
            (event_time, event_type, success, error_code, route, manual_mode,
             selector_name, extraction_source, confidence, duration_ms, result_count, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (old_time, "old_event", 1, "", "", 0, "", "", 0.0, None, None, "{}"),
        )
        cur.execute(
            """
            INSERT INTO telemetry_events
            (event_time, event_type, success, error_code, route, manual_mode,
             selector_name, extraction_source, confidence, duration_ms, result_count, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (recent_time, "recent_event", 1, "", "", 0, "", "", 0.0, None, None, "{}"),
        )
        conn.commit()

    db.cleanup_old_data(days=90, telemetry_days=30)

    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM telemetry_events WHERE event_type = 'old_event'")
        old_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM telemetry_events WHERE event_type = 'recent_event'")
        recent_count = cur.fetchone()[0]

    assert old_count == 0
    assert recent_count == 1


def test_telemetry_jsonl_rolls_with_size_cap(tmp_path: Path):
    db = FlightDatabase(db_path=str(tmp_path / "flight_data.db"))
    db.telemetry_log_path = str(tmp_path / "flightbot_events.jsonl")
    db.telemetry_jsonl_max_bytes = 120
    db.telemetry_jsonl_max_files = 5

    for _ in range(20):
        db.log_telemetry_event(
            event_type="size_test",
            success=True,
            details={"blob": "x" * 200},
        )

    rolled_files = sorted(p.name for p in tmp_path.glob("flightbot_events.jsonl*"))
    assert "flightbot_events.jsonl" in rolled_files
    assert any(name.endswith(".1") for name in rolled_files)
    assert len(rolled_files) <= 5
    assert "flightbot_events.jsonl.5" not in rolled_files

