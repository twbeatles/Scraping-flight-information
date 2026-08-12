# Flight Bot v2.5

Playwright 기반 Interpark 항공권 검색 결과를 PyQt6 데스크톱 UI에서 비교, 저장, 내보내기 하는 도구입니다.

## Current Status

2026-06-11 기준 코드베이스는 책임별 패키지 구조로 분리되어 있습니다. 기존 외부 진입점은 유지하고, 실제 구현은 `core/*`, `scraping/interpark/*`, `scraping/domestic/*`, `scraping/international/*`, `scraping/search_flow/*`로 이동했습니다.

현재 검증 기준:

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
```

최근 로컬 기준선 (2026-08-12):

- `python -m pytest -q` -> `153 passed`
- `pyright --warnings` -> `0 errors, 0 warnings`
- `python scripts\check_tracked_text.py --check-lf` -> tracked text OK
- `python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50` -> 릴리스 전 권장
- `FlightBot_v2.5.spec` PyInstaller 빌드 및 실행 스모크 권장

## Features

- 국내선/국제선, 왕복/편도, 좌석 등급, 성인·소아·유아 인원 검색
- Interpark 동일 출처 API 우선 추출, 실패 시 DOM fallback
- 국내선 공항 단위 URL (`a:GMP`), 국제선 도시 맵 (`c:SEL`)
- 국내선 기본가/혜택가 분리, 왕복 조합, 키 만료 재시도
- 공항·수하물·잔여석·추천 태그 메타 (테이블/export)
- 다중 목적지 검색, 날짜 범위 검색, 캘린더 최저가 보기
- 즐겨찾기, 검색 기록, 세션 저장/복원
- 가격 알림 및 자동 점검 (발동 모달 on/off)
- CSV/Excel 내보내기, formula-like 셀 중립화
- JSONL + SQLite telemetry 기록

## Requirements

- Windows 10/11
- Python 3.10+
- Chrome, Edge 또는 Playwright Chromium

## Install

```powershell
git clone https://github.com/twbeatles/Scraping-flight-information.git
cd Scraping-flight-information
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -c constraints.txt
playwright install chromium
```

`constraints.txt` 없이 `pip install -r requirements.txt`도 가능하지만, 재현 가능한 로컬 검증에는 constraints 사용을 권장합니다.

## Run

```powershell
python gui_v2.py
```

주요 단축키:

| 동작 | 단축키 |
| --- | --- |
| 검색 시작 | `Ctrl+Enter` |
| 강제 재조회 | `Ctrl+Shift+Enter` |
| 검색 취소 | `Esc` |
| 새로고침 | `F5` |
| CSV 내보내기 | `Ctrl+E` |

## Project Structure

```text
Scraping-flight-information/
├─ gui_v2.py                    # GUI 실행 facade
├─ scraper_v2.py                # scraper public facade
├─ scraper_config.py            # Interpark config facade
├─ config.py                    # core public facade
├─ docs/interpark_site_contract.md  # Interpark URL/API/DOM 계약
├─ scraping/interpark/contract/ # endpoints schema, carriers
├─ scraping/domestic/           # 국내선 API/DOM
├─ scraping/international/      # 국제선 API/DOM
├─ scraping/search_flow/        # 검색 orchestration
├─ database.py                  # storage public facade
├─ app/main_window.py           # MainWindow composition
├─ app/mainwindow/              # MainWindow feature mixins
├─ core/
│  ├─ airports.py               # airport/city/airline constants and validation
│  ├─ file_io.py                # atomic text writes
│  ├─ search_params.py          # search parameter schema and normalization
│  └─ preferences.py            # PreferenceManager and user settings
├─ scraping/
│  ├─ playwright_*.py           # compatibility wrappers
│  ├─ interpark/                # URL, selectors, runtime constants, JS builders
│  ├─ search_flow/              # retry, API-first, manual mode orchestration
│  ├─ domestic/                 # domestic API/DOM extraction and round-trip pairing
│  └─ international/            # international API/DOM extraction and normalization
├─ storage/                     # SQLite schema, models, persistence
├─ ui/                          # PyQt panels, dialogs, workers, export helpers
├─ tests/                       # regression tests
└─ scripts/                     # text checks and live smoke utilities
```

## Public Compatibility

아래 import 경로는 외부 스크립트와 기존 테스트 호환을 위해 유지합니다.

```python
import config
import scraper_config
from scraper_v2 import FlightResult, FlightSearcher, PlaywrightScraper, ParallelSearcher
from database import FlightDatabase
from gui_v2 import MainWindow
from ui.components import SearchPanel, ResultTable, FilterPanel
from ui.dialogs import CalendarViewDialog, MultiDestDialog, PriceAlertDialog
from ui.workers import SearchWorker, MultiSearchWorker, DateRangeWorker
```

새 코드에서는 가능하면 책임별 패키지를 직접 사용합니다.

| 영역 | 권장 모듈 |
| --- | --- |
| 공항/도시/항공사 상수 | `core.airports` |
| atomic text write | `core.file_io` |
| 검색 파라미터 정규화 | `core.search_params` |
| 사용자 설정 | `core.preferences` |
| Interpark URL/selector/script | `scraping.interpark.*` |
| 국내선 추출 | `scraping.domestic.*` |
| 국제선 추출 | `scraping.international.*` |
| 검색 흐름 orchestration | `scraping.search_flow.*` |

## Data And Config

- 사용자 설정: `user_preferences.json`
- 기본 DB: `flight_data.db`
- telemetry JSONL: `logs/flightbot_events.jsonl`
- 세션 파일: `flight_session_*.json`
- preferences/session root schema: `schema_version = 2`
- preferences/session JSON은 atomic write를 사용합니다.
- 기본 DB 파일이 손상되어 초기화에 실패하면 timestamp backup으로 격리한 뒤 재생성을 시도합니다.

런타임 산출물, DB, 로그, Playwright profile, 빌드 결과, `.codegraph/`는 `.gitignore`에서 제외합니다.

## Packaging

세 spec 파일은 같은 hidden import 정책을 유지합니다.

- `FlightBot_v2.5.spec`
- `FlightBot_Simple.spec`
- `flight_bot.spec`

필수 포함 범위:

- facade: `database`, `scraper_v2`, `config`, `scraper_config`, `ui.components`, `ui.dialogs`, `ui.styles`, `ui.workers`
- package roots: `app`, `app.mainwindow`, `core`, `scraping`, `storage`, `ui`
- split modules: `core.file_io`, `scraping.interpark.*`, `scraping.domestic.*`, `scraping.international.*`, `scraping.search_flow.*`
- compatibility modules: `scraping.playwright_*`, `scraping.playwright_api`, `scraping.search_sources`, `scraping.manual_reasons`

빌드:

```powershell
python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
```

스모크:

```powershell
dist\FlightBot_v2.5.exe
```

## Quality Checks

로컬에서 변경 전후 아래 명령을 기준으로 확인합니다.

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
git diff --check
```

신규 파일을 추가한 뒤에는 스테이징 후 `check_tracked_text.py --check-lf`를 다시 실행하면 신규 tracked text 파일까지 포함해 점검됩니다.

## Troubleshooting

| 증상 | 확인 |
| --- | --- |
| Playwright 브라우저 실행 실패 | `playwright install chromium` 재실행 |
| PyInstaller 실행 파일에서 import 실패 | spec hiddenimports가 현재 패키지 구조와 맞는지 확인 |
| 검색 결과 0건 또는 수동 모드 진입 | telemetry의 `manual_reason`, `api_total_count`, `fetched_pages`, `api_pages_truncated` 확인 |
| 설정 복원 오류 | `user_preferences.json`의 `schema_version`, 공항 코드, `is_domestic` 확인 |
| DB 마이그레이션/복구 오류 | `storage/schema.py`와 `storage/flight_database.py` 회귀 테스트 및 `.bak` 격리 파일 확인 |

## Changelog

### 2026-06-11

- 국내선/국제선 API pagination에 page cap과 truncation telemetry를 추가했습니다.
- 검색 성공 후 DB 저장/검색 로그/last-result/알림 점검 실패가 결과 렌더링을 막지 않도록 분리했습니다.
- 손상된 SQLite DB 파일은 timestamp backup으로 격리한 뒤 재생성을 시도합니다.
- preferences/session JSON 저장을 atomic write로 변경했습니다.
- 검색 worker 시작 전 취소, 자동 가격 알림 DB 조회 실패, CSV/XLSX formula-like 셀 중립화를 보강했습니다.
- live smoke에 page cap, stale manual reason, browser cleanup 검사를 추가했습니다.
- PyInstaller spec 3종에 `core.file_io` hidden import를 추가했습니다.

### 2026-06-10

- `config.py`, `scraper_config.py`, `scraper_v2.py`, `scraping/playwright_*.py`를 호환 facade로 유지하면서 실제 구현을 책임별 패키지로 분리했습니다.
- `core/*`, `scraping/interpark/*`, `scraping/domestic/*`, `scraping/international/*`, `scraping/search_flow/*`를 추가했습니다.
- MainWindow/SearchPanel mixin의 star import 의존을 명시 import로 정리했습니다.
- 세 PyInstaller spec의 hiddenimports를 새 패키지 구조와 동기화했습니다.
- README, Claude/Gemini 개발 가이드, scraping audit 문서를 현재 코드베이스 우선으로 간략화했습니다.
- `.codegraph/`를 로컬 코드 인덱스 산출물로 ignore 처리했습니다.
