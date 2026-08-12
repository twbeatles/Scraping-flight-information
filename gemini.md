# Flight Bot v2.5 - Gemini 개발 가이드

이 문서는 현재 코드베이스 기준으로 유지한다. 과거 감사에서 이미 처리된 세부 항목은 운영 기준으로 보지 않는다.

## Current Baseline

- 기준일: 2026-08-12
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

- `python -m pytest -q` -> `153 passed`
- `pyright --warnings` -> `0 errors, 0 warnings`
- `python scripts\check_tracked_text.py --check-lf` -> tracked text OK
- live smoke / selector probe -> 릴리스 전 권장
- PyInstaller 빌드 -> 배포 전 권장

## Package Map

```text
core/
├─ airports.py
├─ file_io.py
├─ search_params.py
└─ preferences.py

scraping/interpark/
├─ adapter.py
├─ contract/
│  ├─ carriers.py
│  └─ schemas.py
├─ network_listener.py
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

docs/
└─ interpark_site_contract.md
```

## Key Scraping Rules

- 국내 검색 URL은 공항 단위 (`a:GMP`), 국제는 city map (`c:SEL`).
- 국내 왕복 API-first는 편도 목록으로 종료하지 않고 조합 경로를 사용한다.
- search key 만료 시 soft reload 재시도.
- `FlightResult` 확장 필드(공항/수하물/잔여석 등)는 export·테이블·조합에 전파.
- 비교/알림/테이블 최저가는 `effective_flight_price` 기준.

## Related Docs

- `README.md` — 사용자 설치/실행
- `claude.md` — 에이전트 개발 규칙
- `SCRAPING_AUDIT.md` — 스크래핑 구조 검증 기준
- `PROJECT_AUDIT.md` — 기능 감사 및 remediation 상태
- `docs/interpark_site_contract.md` — Interpark 사이트 계약
