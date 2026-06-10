# Flight Bot implementation/site audit note

- 원 감사일: 2026-05-11
- 현행 정리일: 2026-06-10
- 대상 저장소: `Scraping-flight-information`

## Status

2026-05-11 감사에서 확인된 Interpark API-first 실패, DOM fallback 의존, live smoke import path, DB migration 순서 문제는 현재 코드베이스에 반영 완료된 이력이다. 이 파일은 열린 항목 목록이 아니라, 해당 감사가 현재 구조로 대체되었음을 기록하는 짧은 메모로 유지한다.

## Current Implementation Locations

| 과거 단일/대형 모듈 | 현재 위치 |
| --- | --- |
| `config.py` 상수/설정 | `core.airports`, `core.search_params`, `core.preferences` |
| `scraper_config.py` Interpark 설정 | `scraping.interpark.runtime`, `scraping.interpark.urls`, `scraping.interpark.selectors`, `scraping.interpark.scripts` |
| `scraping/playwright_results.py` 국제선 추출 | `scraping.international.*` |
| `scraping/playwright_domestic.py` 국내선 추출 | `scraping.domestic.*` |
| `scraping/playwright_search.py` 검색 흐름 | `scraping.search_flow.*` |

기존 파일들은 외부 import 호환을 위한 facade/wrapper로 남아 있다.

## Current Validation

```text
python -m pytest -q
-> 111 passed

pyright --warnings
-> 0 errors, 0 warnings

python scripts\check_tracked_text.py --check-lf
-> Checked 112 tracked text files: OK

python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
-> dist\FlightBot_v2.5.exe generated

dist\FlightBot_v2.5.exe
-> 6 second smoke passed
```

## Current Priority

- 운영 기준은 `README.md`, `claude.md`, `gemini.md`, `SCRAPING_AUDIT.md`의 2026-06-10 구조 설명을 우선한다.
- 과거 상세 실패 로그는 현재 수정 완료된 내용이므로 이 파일에 유지하지 않는다.
- 향후 실사이트 계약이 바뀌면 새 감사 문서를 만들고, 이 파일에는 오래된 실패 항목을 다시 누적하지 않는다.
