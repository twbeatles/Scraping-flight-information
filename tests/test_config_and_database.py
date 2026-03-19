import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import config
from app.session_manager import SessionManager
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
    restored_params, restored, _, _ = db.get_last_search_results()

    assert len(restored) == 1
    assert restored[0].confidence == 0.88
    assert restored[0].extraction_source == "international_primary"
    assert restored_params["is_domestic"] is False


def test_last_search_metadata_persists_sel_domestic_route(tmp_path: Path):
    db = FlightDatabase(db_path=str(tmp_path / "flight_data.db"))
    search_params = {
        "origin": "SEL",
        "dest": "CJU",
        "dep": "20260301",
        "ret": "20260305",
        "adults": 2,
        "cabin_class": "ECONOMY",
        "is_domestic": True,
    }
    db.save_last_search_results(
        search_params,
        [FlightResult(airline="Domestic", price=111000, departure_time="10:00", arrival_time="11:00")],
    )

    restored_params, _, _, _ = db.get_last_search_results()

    assert restored_params["origin"] == "SEL"
    assert restored_params["dest"] == "CJU"
    assert restored_params["is_domestic"] is True


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


def test_import_settings_trims_search_history_to_20(tmp_path: Path):
    pref_path = tmp_path / "prefs.json"
    import_path = tmp_path / "import.json"

    prefs = PreferenceManager(filepath=str(pref_path))
    big_history = [
        {"origin": "ICN", "dest": "NRT", "dep": f"202603{(i % 28) + 1:02d}", "timestamp": f"2026-03-{(i % 28) + 1:02d} 10:00"}
        for i in range(35)
    ]
    import_payload = {"search_history": big_history}
    import_path.write_text(json.dumps(import_payload, ensure_ascii=False), encoding="utf-8")

    ok = prefs.import_settings(str(import_path))

    assert ok is True
    assert len(prefs.get_history()) == 20


def test_preference_manager_normalizes_legacy_search_payloads(tmp_path: Path):
    pref_path = tmp_path / "prefs.json"
    pref_path.write_text(
        json.dumps(
            {
                "custom_presets": {"abc": "커스텀"},
                "last_search": {
                    "origin": "SEL (서울(도시))",
                    "dest": "CJU (제주)",
                    "dep": "2026-03-01",
                    "ret": "2026-03-05",
                    "adults": "2",
                    "cabin_class": "business",
                },
                "saved_profiles": {
                    "legacy": {
                        "origin": "SEL (서울(도시))",
                        "dest": "CJU (제주)",
                        "dep": "2026-03-01",
                        "ret": "2026-03-05",
                    }
                },
                "search_history": [
                    {
                        "origin": "SEL (서울(도시))",
                        "dest": "CJU (제주)",
                        "dep": "2026-03-01",
                        "ret": "2026-03-05",
                        "timestamp": "2026-03-01 10:00",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    prefs = PreferenceManager(filepath=str(pref_path))
    last_search = prefs.get_last_search()
    profile = prefs.get_profile("legacy")
    history = prefs.get_history()

    assert prefs.preferences["schema_version"] == config.SEARCH_PARAMS_SCHEMA_VERSION
    assert last_search["origin"] == "SEL"
    assert last_search["dest"] == "CJU"
    assert last_search["dep"] == "20260301"
    assert last_search["cabin_class"] == "BUSINESS"
    assert last_search["adults"] == 2
    assert last_search["is_domestic"] is True
    assert profile["origin"] == "SEL"
    assert history[0]["origin"] == "SEL"


def test_session_manager_load_normalizes_legacy_session_payload(tmp_path: Path):
    session_path = tmp_path / "legacy_session.json"
    session_path.write_text(
        json.dumps(
            {
                "saved_at": "2026-03-19T12:00:00",
                "search_params": {
                    "origin": "SEL (서울(도시))",
                    "dest": "CJU (제주)",
                    "dep": "2026-03-01",
                    "ret": "2026-03-05",
                    "adults": "2",
                },
                "results": [
                    {
                        "airline": "Legacy",
                        "price": 123000,
                        "departure_time": "10:00",
                        "arrival_time": "11:00",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    params, results, saved_at = SessionManager.load_session(str(session_path))

    assert params["origin"] == "SEL"
    assert params["dest"] == "CJU"
    assert params["dep"] == "20260301"
    assert params["is_domestic"] is True
    assert params["adults"] == 2
    assert saved_at == "2026-03-19T12:00:00"
    assert len(results) == 1


def test_add_price_alert_persists_adults_and_default_error(tmp_path: Path):
    db = FlightDatabase(db_path=str(tmp_path / "flight_data.db"))

    db.add_price_alert("ICN", "NRT", "20260320", None, 250000, "BUSINESS", adults=3)
    alerts = db.get_all_alerts()

    assert len(alerts) == 1
    assert alerts[0].adults == 3
    assert alerts[0].last_error == ""

