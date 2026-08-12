# Flight Bot implementation/site audit note

- 원 감사일: 2026-05-11
- 현행 정리일: 2026-08-12
- 대상 저장소: `Scraping-flight-information`

## Status

2026-05-11 감사에서 확인된 Interpark API-first 실패, DOM fallback 의존, live smoke import path, DB migration 순서 문제는 현재 코드베이스에 반영 완료된 이력이다.

이 파일은 **열린 이슈 목록이 아니다.** 과거 감사가 현재 구조로 대체되었음을 기록하는 짧은 메모로 유지한다.

## Current Implementation Locations

| 과거 단일/대형 모듈 | 현재 위치 |
| --- | --- |
| `config.py` 상수/설정 | `core.airports`, `core.search_params`, `core.preferences` |
| `scraper_config.py` Interpark 설정 | `scraping.interpark.runtime`, `urls`, `selectors`, `scripts`, `adapter`, `contract/*` |
| `scraping/playwright_results.py` 국제선 추출 | `scraping.international.*` |
| `scraping/playwright_domestic.py` 국내선 추출 | `scraping.domestic.*` |
| `scraping/playwright_search.py` 검색 흐름 | `scraping.search_flow.*` |

기존 파일들은 외부 import 호환을 위한 facade/wrapper로 남아 있다.

## Where To Look Now

운영/개발 시 **현재 기준 문서**를 우선한다.

1. `README.md` — 설치/실행/구조
2. `claude.md` / `gemini.md` — 에이전트 개발 규칙
3. `SCRAPING_AUDIT.md` — 스크래핑 검증 기준
4. `PROJECT_AUDIT.md` — 기능 감사 및 remediation 상태
5. `docs/interpark_site_contract.md` — 실사이트 URL/API/DOM 계약

검증 기준선(2026-08-12):

```text
python -m pytest -q
-> 153 passed
```

## Current Priority

- 과거 상세 실패 로그는 이 파일에 다시 누적하지 않는다.
- 실사이트 계약 변경 시 `docs/interpark_site_contract.md`와 `SCRAPING_AUDIT.md`를 갱신한다.
- 기능 이슈 추적은 `PROJECT_AUDIT.md` Remediation Status를 사용한다.
