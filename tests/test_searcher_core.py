from datetime import datetime, timedelta
from typing import Any, cast
import scraper_config
from scraper_v2 import (
    FlightResult,
    FlightSearcher,
    ManualModeActivationError,
    PlaywrightScraper,
    ParallelSearcher,
)
from ui.workers import AlertAutoCheckWorker, DateRangeWorker, MultiSearchWorker, SearchWorker

class _PlaywrightPageStubMixin:
    def on(self, _event, _handler):
        return None

def test_enter_manual_mode_reinitializes_when_session_missing(monkeypatch):
    scraper = PlaywrightScraper()
    scraper.page = None
    scraper.context = None
    scraper.browser = None

    calls = {"init": 0, "goto": 0}

    class _FakePage(_PlaywrightPageStubMixin):
        def goto(self, *args, **kwargs):
            calls["goto"] += 1

    class _FakeContext:
        def new_page(self):
            return _FakePage()

    def _fake_init_browser(*args, **kwargs):
        calls["init"] += 1
        cast(Any, scraper).context = _FakeContext()
        cast(Any, scraper).browser = object()

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *args, **kwargs: {"found": True})
    monkeypatch.setattr(scraper, "close", lambda: None)

    entered = scraper._enter_manual_mode(
        url="https://example.com/search",
        profile_dir="playwright_profile",
        is_domestic=False,
        log_func=lambda _msg: None,
        reopen_visible=False,
    )

    assert entered is True
    assert scraper.manual_mode is True
    assert calls["init"] == 1
    assert calls["goto"] == 1

def test_flight_searcher_uses_cache_for_same_query(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    FlightSearcher.clear_cache()

    class _FakeSource:
        source_id = "fake"
        metadata = {}

        def __init__(self):
            self.calls = 0

        def build_search_url(self, params):
            return "https://example.test"

        def search(self, *args, **kwargs):
            self.calls += 1
            return [FlightResult(airline="CacheAir", price=150000, departure_time="10:00", arrival_time="12:00")]

        def extract_manual(self):
            return []

        def is_manual_mode(self):
            return False

        def close(self):
            return None

    searcher = FlightSearcher()
    fake_source = _FakeSource()
    searcher.source = fake_source
    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)
    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_source.calls == 1
    assert second[0].price == first[0].price

    FlightSearcher.clear_cache()

def test_flight_searcher_cache_expires_after_ttl(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 1)
    FlightSearcher.clear_cache()

    class _FakeSource:
        source_id = "fake"
        metadata = {}

        def __init__(self):
            self.calls = 0

        def build_search_url(self, params):
            return "https://example.test"

        def search(self, *args, **kwargs):
            self.calls += 1
            return [
                FlightResult(
                    airline="CacheAir",
                    price=120000 + self.calls,
                    departure_time="09:00",
                    arrival_time="11:00",
                )
            ]

        def extract_manual(self):
            return []

        def is_manual_mode(self):
            return False

        def close(self):
            return None

    searcher = FlightSearcher()
    fake_source = _FakeSource()
    searcher.source = fake_source
    dep = (datetime.now() + timedelta(days=8)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    with FlightSearcher._cache_lock:
        for key, (saved_at, payload) in list(FlightSearcher._search_cache.items()):
            FlightSearcher._search_cache[key] = (saved_at - 5, payload)

    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_source.calls == 2
    assert second[0].price != first[0].price

    FlightSearcher.clear_cache()

def test_search_worker_passes_force_refresh(monkeypatch):
    calls = {"force_refresh": None}

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            calls["force_refresh"] = kwargs.get("force_refresh")
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = SearchWorker("ICN", "NRT", "20260301", None, 1, max_results=10, force_refresh=True)
    worker.run()

    assert calls["force_refresh"] is True

def test_search_worker_emits_error_on_manual_mode_activation_failure(monkeypatch):
    class _FakeSearcher:
        def search(self, *args, **kwargs):
            raise ManualModeActivationError("manual activation failed")

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = SearchWorker("ICN", "NRT", "20260301", None, 1, max_results=10)
    errors = []
    worker.error.connect(lambda msg: errors.append(msg))
    worker.run()

    assert errors
    assert "manual activation failed" in errors[0]

def test_playwright_search_retries_on_network_error(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.calls = 0

        def goto(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise Exception("temporary network failure")

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": True, "selector": "li[data-index]"})
    monkeypatch.setattr(
        scraper,
        "_extract_prices",
        lambda: [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")],
    )
    monkeypatch.setattr(scraper, "close", lambda: None)
    monkeypatch.setattr("scraper_v2.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("ICN", "NRT", "20260301", None, adults=1, cabin_class="ECONOMY", max_results=10)

    assert len(results) == 1
    assert page.calls == 2

def test_playwright_search_closes_between_network_retries(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.calls = 0

        def goto(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise Exception("temporary network failure")

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()
    close_calls = {"count": 0}

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    def _fake_close():
        close_calls["count"] += 1
        scraper.page = None
        scraper.context = None
        scraper.browser = None
        scraper.playwright = None
        scraper.manual_mode = False

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": True, "selector": "li[data-index]"})
    monkeypatch.setattr(
        scraper,
        "_extract_prices",
        lambda: [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")],
    )
    monkeypatch.setattr(scraper, "close", _fake_close)
    monkeypatch.setattr("scraper_v2.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("ICN", "NRT", "20260301", None, adults=1, cabin_class="ECONOMY", max_results=10)

    assert len(results) == 1
    assert page.calls == 2
    assert close_calls["count"] >= 2

def test_playwright_background_mode_disables_manual_fallback(monkeypatch):
    class _FakePage:
        def goto(self, *_args, **_kwargs):
            return None

    class _FakeContext:
        def __init__(self):
            self._page = _FakePage()

        def new_page(self):
            return self._page

        def close(self):
            return None

    scraper = PlaywrightScraper()

    def _fake_init_browser(_log=None, _user_data_dir=None, headless=False):
        cast(Any, scraper).context = _FakeContext()

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": False, "selector": ""})
    monkeypatch.setattr(scraper, "close", lambda: None)

    results = scraper.search(
        "ICN",
        "NRT",
        "20260301",
        None,
        adults=1,
        cabin_class="ECONOMY",
        max_results=10,
        background_mode=True,
    )

    assert results == []
    assert scraper.manual_mode is False

