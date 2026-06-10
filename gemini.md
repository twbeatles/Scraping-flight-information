# Flight Bot v2.5 - Gemini 개발 가이드

이 문서는 현재 코드베이스 기준으로 유지한다. 과거 감사에서 이미 처리된 세부 항목은 운영 기준으로 보지 않는다.

## Current Baseline

- 기준일: 2026-06-11
- 실행: `python gui_v2.py`
- GUI: PyQt6
- Scraper: Playwright
- DB: SQLite
- Packaging: PyInstaller

현재 구조는 facade 유지 + 책임별 구현 패키지 분리 방식이다.

| 공개 경로 | 실제 구현 |
| --- | --- |
| `config.py` | `core.airports`, `core.file_io`, `core.search_params`, `core.preferences` |
| `scraper_config.py` | `scraping.interpark.*` |
| `scraper_v2.py` | `scraping.models`, `scraping.playwright_scraper`, `scraping.parallel` |
| `scraping.playwright_results` | `scraping.international.*` compatibility wrapper |
| `scraping.playwright_domestic` | `scraping.domestic.*` compatibility wrapper |
| `scraping.playwright_search` | `scraping.search_flow.*` compatibility wrapper |
| `database.py` | `storage.*` |
| `gui_v2.py` | `app.main_window` |

## Validation Baseline

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
```

최근 확인 결과:

- `python -m pytest -q` -> `123 passed`
- `pyright --warnings` -> `0 errors, 0 warnings`
- `python scripts\check_tracked_text.py --check-lf` -> `Checked 142 tracked text files: OK`
- live smoke with page-cap guard -> 국내선/국제선 실사이트 검색 통과
- `FlightBot_v2.5.exe` 6초 실행 스모크 통과

## Package Map

```text
core/
├─ airports.py
├─ file_io.py
├─ search_params.py
└─ preferences.py

scraping/interpark/
├─ runtime.py
├─ urls.py
├─ selectors.py
└─ scripts/

scraping/domestic/
├─ api.py
├─ dom.py
├─ helpers.py
└─ results.py

scraping/international/
├─ api.py
├─ dom.py
├─ helpers.py
├─ normalizer.py
├─ orchestration.py
└─ sorting.py

scraping/search_flow/
├─ api_first.py
├─ domestic_flow.py
├─ manual_mode.py
└─ orchestration.py
```

## Stable Interfaces

리팩터링 중 아래 경로와 타입은 호환성을 유지해야 한다.

```python
import config
import scraper_config
from scraper_v2 import FlightResult, FlightSearcher, PlaywrightScraper, ParallelSearcher
from database import FlightDatabase
from gui_v2 import MainWindow
```

핵심 계약:

- `FlightResult`
- `PreferenceManager`
- `FlightDatabase`
- `ScraperScripts`
- `build_interpark_search_url()`
- `normalize_search_params()`

## Functional Rules

- API-first 추출을 우선하고, 실패 시 DOM fallback 또는 수동 모드로 전환한다.
- API pagination은 runtime page cap을 지키고 truncation telemetry를 남긴다.
- API 성공 후 pre-wait 실패 사유를 최종 실패 사유로 유지하지 않는다.
- 검색 결과 shape, DB schema, 세션 JSON schema, preferences JSON schema는 임의 변경하지 않는다.
- preferences/session JSON 저장은 atomic write를 사용한다.
- 손상된 기본 DB는 timestamp backup으로 격리한 뒤 재생성을 시도한다.
- `FlightResult.price`는 국내선 기본가 기준이며 혜택가는 별도 필드에 보존한다.
- 검색 파라미터는 `origin`, `dest`, `dep`, `ret`, `adults`, `cabin_class`, `is_domestic`를 기준으로 저장/복원한다.
- `user_preferences.json`과 세션 JSON은 `schema_version = 2`를 유지한다.
- telemetry는 JSONL과 DB 양쪽에 기록한다.
- 다중 목적지/날짜 범위/자동 가격 알림 검색은 background mode로 실행한다.
- 자동 가격 알림 DB 조회 실패는 worker 실행 없이 상태/log/telemetry로 노출한다.
- CSV/Excel export는 formula-like 셀을 중립화한다.

## Packaging And Ignore Rules

- spec 3종은 facade와 새 split package, `core.file_io`를 모두 hiddenimports에 포함한다.
- `.gitignore`는 build/dist, logs, DB, sessions, Playwright profile, test cache, `.codegraph/`를 제외한다.
- 신규 런타임 산출물은 커밋하지 않는다.

## Change Checklist

1. 코드 이동 시 facade re-export가 기존과 같은지 테스트한다.
2. 새 모듈을 추가하면 spec hiddenimports를 점검한다.
3. 문서에는 현재 코드 기준만 남기고 이미 완료된 수정 이력은 길게 유지하지 않는다.
4. 커밋 전 `pytest`, `pyright`, LF check, `git diff --check`를 실행한다.
