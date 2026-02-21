from pathlib import Path

from config import PreferenceManager
from database import FlightDatabase
from scraper_v2 import FlightResult


def test_default_max_results_is_1000(tmp_path: Path):
    pref_path = tmp_path / "prefs.json"
    prefs = PreferenceManager(filepath=str(pref_path))
    assert prefs.get_max_results() == 1000


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


def test_add_price_history_batch_accepts_flight_results(tmp_path: Path):
    db_path = tmp_path / "flight_data.db"
    db = FlightDatabase(db_path=str(db_path))

    dep_date = "20260301"
    results = [
        FlightResult(airline="A", price=210000, departure_time="10:00", arrival_time="12:00"),
        FlightResult(airline="B", price=190000, departure_time="11:00", arrival_time="13:00"),
        FlightResult(airline="C", price=230000, departure_time="12:00", arrival_time="14:00"),
    ]

    db.add_price_history_batch("ICN", "NRT", dep_date, results)
    history = db.get_price_history("ICN", "NRT", days=365)

    assert history
    assert history[-1].price == 190000
    assert history[-1].airline == "B"

