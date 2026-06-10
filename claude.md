# Flight Bot v2.5 - Claude 개발 가이드

이 문서는 현재 코드베이스 기준만 기록한다. 오래된 감사 결과나 이미 수정된 이슈 목록보다 이 파일의 현재 구조와 검증 기준을 우선한다.

## Current Baseline

- 기준일: 2026-06-10
- 실행 진입점: `python gui_v2.py`
- 주요 기술: Python 3.10+, PyQt6, Playwright, SQLite, PyInstaller
- 공개 facade 유지: `config.py`, `scraper_config.py`, `scraper_v2.py`, `database.py`, `gui_v2.py`, `ui.components`, `ui.dialogs`, `ui.styles`, `ui.workers`, `scraping.playwright_*`
- 실제 구현 위치: `core/*`, `scraping/interpark/*`, `scraping/domestic/*`, `scraping/international/*`, `scraping/search_flow/*`

검증 기준:

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
```

최근 확인 결과:

- `python -m pytest -q` -> `111 passed`
- `pyright --warnings` -> `0 errors, 0 warnings`
- `python scripts\check_tracked_text.py --check-lf` -> `Checked 112 tracked text files: OK`
- 신규 패키지 파일 LF/UTF-8 점검 -> `Checked 30 new package files: OK`
- `dist\FlightBot_v2.5.exe` 6초 실행 스모크 통과

## Architecture

```text
gui_v2.py
└─ app/main_window.py
   └─ app/mainwindow/*              # MainWindow feature mixins

scraper_v2.py
└─ scraping/playwright_scraper.py
   ├─ scraping/search_flow/*        # retry, API-first, manual-mode orchestration
   ├─ scraping/domestic/*           # domestic API/DOM extraction
   ├─ scraping/international/*      # international API/DOM extraction
   └─ scraping/interpark/*          # URLs, selectors, runtime constants, JS builders

config.py
└─ core/*
   ├─ airports.py
   ├─ search_params.py
   └─ preferences.py

database.py
└─ storage/*
```

## Module Responsibilities

| 모듈 | 책임 |
| --- | --- |
| `core.airports` | 공항/도시/항공사 상수, 공항 코드 검증, 항공사 분류 |
| `core.search_params` | 검색 파라미터 스키마, 날짜 정규화, 국내선 추론 |
| `core.preferences` | `PreferenceManager`, 설정 import/export, 히스토리/프로필 |
| `scraping.interpark.runtime` | timeout, retry, cache, scroll 튜닝 상수 |
| `scraping.interpark.urls` | Interpark URL/date/location builder |
| `scraping.interpark.selectors` | wait selector와 regex pattern |
| `scraping.interpark.scripts` | 기존 `ScraperScripts` static method 호환 class |
| `scraping.domestic` | 국내선 API-first 추출, DOM fallback, 왕복 조합 |
| `scraping.international` | 국제선 API-first 추출, DOM fallback, fare/benefit 정규화 |
| `scraping.search_flow` | 수동 모드, API-first 시도, 재시도 orchestration |
| `app.mainwindow.*` | MainWindow 기능별 mixin |
| `ui.search_panel_*` | SearchPanel build/action/state 분리 |
| `storage.*` | SQLite schema, migration, persistence |

## Compatibility Contracts

아래 계약은 리팩터링 중 깨면 안 된다.

- `FlightResult` shape와 `to_dict()` 결과
- `PreferenceManager` public method와 `user_preferences.json` schema
- `FlightDatabase` public API와 SQLite schema migration
- `ScraperScripts` static method 이름
- `build_interpark_search_url()`
- `normalize_search_params()`
- `from scraper_v2 import FlightSearcher, PlaywrightScraper, ParallelSearcher`
- `from database import FlightDatabase`
- `from gui_v2 import MainWindow`

## Scraping Rules

- 국제선과 국내선 모두 Interpark 동일 출처 API를 먼저 시도한다.
- API 성공 시 DOM fallback을 실행하지 않는다.
- API 실패 또는 key 미확인 시에만 DOM fallback과 수동 모드로 내려간다.
- `manual_reason`, `api_total_count`, `fetched_pages`, `api_item_count`, `dom_seen_indices`, `dom_gap_detected`를 telemetry에 남긴다.
- 국내선 canonical `price`는 기본가이고, 혜택가는 `benefit_price`/`benefit_label`에 보존한다.
- 국내선 왕복 dedup key는 시간, 편명, API key, 혜택가/혜택 라벨을 포함해야 한다.

## UI And Data Rules

- 검색 파라미터 공용 schema: `origin`, `dest`, `dep`, `ret`, `adults`, `cabin_class`, `is_domestic`
- `is_domestic`가 없는 구 payload는 국내선 공항 코드 기준으로 추론한다.
- `user_preferences.json`과 세션 JSON root는 `schema_version = 2`를 유지한다.
- 검색 패널 복원은 국내선/국제선 모드를 먼저 맞춘 뒤 공항 코드를 적용한다.
- 자동 가격 알림 실패는 모달 대신 `last_error`, 로그, 목록 상태로 노출한다.
- CSV/Excel export는 `ui.export_helpers`의 공통 컬럼 정책을 따른다.

## Packaging Rules

세 spec 파일은 새 패키지와 facade를 모두 hiddenimports에 유지해야 한다.

- `FlightBot_v2.5.spec`
- `FlightBot_Simple.spec`
- `flight_bot.spec`

필수 범위:

- `core.airports`, `core.search_params`, `core.preferences`
- `scraping.interpark.*`
- `scraping.domestic.*`
- `scraping.international.*`
- `scraping.search_flow.*`
- 기존 `scraping.playwright_*`, `scraping.playwright_api`, `scraping.search_sources`, `scraping.manual_reasons`
- `ui.search_panel_params`, `ui.airport_options`, `ui.export_helpers`
- `storage.schema`, `storage.flight_database`, `storage.db_favorites`

## Editing Checklist

1. 기존 facade import 경로를 유지한다.
2. 동작 변경이 있으면 테스트를 추가하거나 기존 테스트를 갱신한다.
3. 새 모듈을 추가하면 PyInstaller hiddenimports와 문서를 함께 확인한다.
4. 로컬 산출물은 `.gitignore`에만 반영하고 커밋하지 않는다.
5. 커밋 전 `pytest`, `pyright`, text LF check, `git diff --check`를 실행한다.
