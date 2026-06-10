# Project Audit

Generated: 2026-06-11
Implementation status: Completed on 2026-06-11

## 1. Executive Summary

Overall residual risk: Low-Medium.

The audit findings identified runtime risks around live API pagination, stale telemetry state, SQLite failure isolation, cancellation timing, spreadsheet export safety, and non-atomic JSON writes. The proposed fix plan has been implemented and validated.

Implemented fixes:

- API pagination now has explicit domestic/international page caps and truncation telemetry.
- Domestic pre-wait API failure reasons are cleared after later API/DOM success so stale failures do not masquerade as final failures.
- DB startup now attempts corrupt-file backup and recreation; search-result rendering is no longer blocked by independent persistence failures.
- Single-search workers honor cancellation before invoking `FlightSearcher.search()`.
- CSV/XLSX export neutralizes formula-like external values.
- Preferences and session JSON writes now use same-directory atomic replacement.
- Live smoke checks now fail on page-cap violations, stale manual reasons after success, or browser cleanup failure.

Validation performed after implementation:

- `python -m pytest -q` -> `123 passed`
- `pyright --warnings` -> `0 errors, 0 warnings`
- `python scripts\check_tracked_text.py --check-lf` -> `Checked 142 tracked text files: OK`
- `python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50`
  - Domestic `GMP->CJU`: 5 results, `fetched_pages=10`, `api_pages_truncated=False`, `cleanup_ok=True`
  - International `ICN->NRT`: 5 results, `fetched_pages=50`, `api_pages_truncated=True`, `cleanup_ok=True`
- `python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec` -> `dist\FlightBot_v2.5.exe` generated
- `dist\FlightBot_v2.5.exe` -> started and survived 6 second smoke

Residual risks are mostly external-service risks: Interpark API response contracts can change, live traffic can be throttled, and the UI still depends on browser automation availability.

## 2. Project Understanding

`README.md`, `claude.md`, `gemini.md`, and `SCRAPING_AUDIT.md` now describe the current package split and the 2026-06-11 runtime hardening baseline.

Main execution flow:

1. `gui_v2.py` imports and launches `app.main_window.MainWindow`.
2. `MainWindow` composes feature mixins under `app/mainwindow/*`.
3. `SearchPanel` validates user input and emits `search_requested`.
4. `SearchSingleMixin._start_search()` creates `ui.workers.SearchWorker`.
5. `SearchWorker.run()` now checks cancellation before calling `scraper_v2.FlightSearcher.search()`.
6. `FlightSearcher` creates `InterparkAirSource`, applies cache, and dispatches to `PlaywrightScraper.search()`.
7. `scraping.search_flow.orchestration.run_search()` handles browser setup, API-first extraction, DOM fallback, manual mode, retry, telemetry, and cleanup.
8. Results flow back to `_search_finished()`, which renders results first and isolates DB/log/last-result/alert persistence failures.

Storage/config flow:

- Preferences: `core.preferences.PreferenceManager`, now backed by `core.file_io.write_text_atomic()`.
- Sessions: `app.session_manager.SessionManager`, now backed by `core.file_io.write_text_atomic()`.
- DB: `storage.flight_database.FlightDatabase`, now attempts corrupt DB backup/recreation on initialization failure.
- Telemetry: SQLite `telemetry_events` plus JSONL at `logs/flightbot_events.jsonl`.

CodeGraph-derived impact boundaries from the audit:

- `FlightSearcher` has broad impact across workers, manual mode, live smoke, perf benchmark, and tests, so worker cancellation was implemented in `SearchWorker` without altering `FlightSearcher` public behavior.
- `_fetch_international_result_pages` has narrow impact inside `scraping/international/api.py`, so page caps were added there with direct telemetry.
- `export_flights_to_csv` and `export_flights_to_excel` share `ui.export_helpers`, so formula neutralization was centralized in export row generation.

## 3. High-Risk Issues

### Issue 1 - API extraction ignored `max_results` until after full pagination

위치: `scraping/international/api.py::_fetch_international_result_pages`, `scraping/domestic/api.py::extract_domestic_api_flights_data`, `scraping/interpark/runtime.py`

문제:

The API extractors could fetch all reported result pages before the later result limit was applied.

영향:

Low `max_results` searches could still perform excessive remote pagination, delaying UI/background jobs and increasing throttling risk.

근거:

The live smoke before implementation returned only 5 international results but fetched 161 pages and 3217 API items.

권장 수정 방향:

Implemented. Added `DOMESTIC_API_MAX_PAGES=30` and `INTERNATIONAL_API_MAX_PAGES=50`, capped API loops, and recorded `api_page_cap`, `api_pages_truncated`, `api_total_pages_estimated`, and `api_fetched_pages`.

우선순위: High

상태: Completed

### Issue 2 - Domestic transient API failure remained after later success

위치: `scraping/domestic/api.py`, `scraping/domestic/results.py`, `scraping/search_flow/domestic_flow.py`

문제:

An early missing-key/pre-wait failure reason could remain on the scraper after a later API or DOM success.

영향:

Telemetry and smoke checks could report a failed API state for a successful search, making diagnosis unreliable.

근거:

The live smoke showed a successful domestic API result while also retaining `api_failure_reason=domestic_api_key_missing`.

권장 수정 방향:

Implemented. Added `clear_domestic_api_failure_after_success()` and moved early failure state to `prewait_api_failure_reason` instead of final `api_failure_reason`.

우선순위: Medium

상태: Completed

### Issue 3 - DB failures could block startup or break successful search completion

위치: `storage/flight_database.py`, `app/main_window.py`, `app/mainwindow/search_single.py`

문제:

SQLite initialization failures and post-search persistence failures were not sufficiently isolated from startup or result rendering.

영향:

A corrupt DB could prevent startup; a successful search could be interrupted by price-history, search-log, last-result, or alert persistence failures.

근거:

`MainWindow` constructed `FlightDatabase()` directly and `_search_finished()` performed multiple DB writes in sequence before all user-visible completion work was isolated.

권장 수정 방향:

Implemented. `FlightDatabase` now backs up corrupt primary DB files and retries initialization. `MainWindow` falls back to a temp DB if primary initialization still fails. `_search_finished()` renders results and delegates independent persistence steps to `_persist_successful_search()` with per-step warning handling.

우선순위: High

상태: Completed

### Issue 4 - Single-search cancellation could race before `run()` started work

위치: `ui/workers_search.py::SearchWorker.run`

문제:

Cancellation requested before the worker thread entered `run()` could still allow `searcher.search()` to start.

영향:

The UI could show cancellation while a browser-backed search had already started in the background.

근거:

The previous `run()` path checked cancellation only after calling the searcher.

권장 수정 방향:

Implemented. `SearchWorker.run()` now checks `is_cancelled()` before invoking `self.searcher.search()`.

우선순위: Medium

상태: Completed

### Issue 5 - CSV/XLSX export could preserve spreadsheet formulas from external data

위치: `ui/export_helpers.py`

문제:

External route/airline/time strings could be written directly into spreadsheet cells even when they started with formula trigger characters.

영향:

Opening exported CSV/XLSX files in spreadsheet software could evaluate untrusted formula-like content.

근거:

`flight_export_rows()` returned raw values from `FlightResult` fields.

권장 수정 방향:

Implemented. Added `sanitize_export_cell()` and applied it to every exported cell for CSV and XLSX paths.

우선순위: Medium

상태: Completed

### Issue 6 - Preferences and sessions were not written atomically

위치: `core/preferences.py`, `app/session_manager.py`, `core/file_io.py`

문제:

JSON settings/session files were written directly to their final paths.

영향:

An interrupted write could leave user preferences or saved sessions truncated or invalid.

근거:

Direct `open(..., "w")` writes were used for preference/session persistence.

권장 수정 방향:

Implemented. Added `core.file_io.write_text_atomic()` and updated preference export/save plus session save to use same-directory temp files and `os.replace()`.

우선순위: Low-Medium

상태: Completed

## 4. Potential Functional Gaps

- 추정: API page caps reduce excessive fetches but may omit very deep result pages. Current telemetry exposes `api_pages_truncated=True` so future UI copy or filters can make truncation visible to users if needed.
- 추정: Corrupt DB recovery preserves the bad DB as a timestamped `.bak`, but there is no in-app restore UI for that backup.
- 추정: Live API smoke is intentionally short and route-specific. It should remain a release gate, but it does not prove every route/date/provider combination.

## 5. Recommended Fix Plan

### 1단계 - 즉시 수정해야 할 문제

Completed.

- API pagination page caps and truncation telemetry.
- DB initialization recovery and isolated post-search persistence.
- Spreadsheet formula-like value neutralization.

### 2단계 - 안정성 개선

Completed.

- Worker pre-run cancellation guard.
- Domestic stale failure reason cleanup.
- Atomic preferences/session writes.
- Auto alert DB-read failure isolation.
- Live smoke threshold checks.

### 3단계 - 구조 개선

Completed for this scope.

- Shared atomic file IO utility.
- Shared export sanitization utility.
- Docs/spec sync for the added runtime module.

Deferred as future product work:

- Optional in-app DB backup restore flow.
- Optional UI indicator when live API results were truncated by page cap.

## 6. Test Recommendations

Implemented regression tests:

- Worker cancellation before search start.
- Domestic and international API pagination cap behavior.
- Domestic pre-wait failure cleanup after later success.
- Atomic write failure keeps existing file content.
- Corrupt DB file recovery.
- Search result rendering despite DB persistence failures.
- CSV/XLSX formula-like export neutralization.
- Auto alert DB read failure logging without worker execution.
- Live smoke threshold helper for page-cap and stale manual-reason detection.

Recommended ongoing checks before release:

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
git diff --check
```
