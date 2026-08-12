# Flight Bot v2.5 - Claude 개발 가이드

이 문서는 현재 코드베이스 기준만 기록한다. 오래된 감사 결과나 이미 수정된 이슈 목록보다 이 파일의 현재 구조와 검증 기준을 우선한다.

## Current Baseline

- 기준일: 2026-08-12
- 실행 진입점: `python gui_v2.py`
- 주요 기술: Python 3.10+, PyQt6, Playwright, SQLite, PyInstaller
- 공개 facade 유지: `config.py`, `scraper_config.py`, `scraper_v2.py`, `database.py`, `gui_v2.py`, `ui.components`, `ui.dialogs`, `ui.styles`, `ui.workers`, `scraping.playwright_*`
- 실제 구현 위치: `core/*`, `scraping/interpark/*`, `scraping/domestic/*`, `scraping/international/*`, `scraping/search_flow/*`

검증 기준:

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
- live smoke / selector probe -> 릴리스 전 권장

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
   ├─ file_io.py
   ├─ search_params.py
   └─ preferences.py

database.py
└─ storage/*
```

## Module Responsibilities

| 모듈 | 책임 |
| --- | --- |
| `core.airports` | 공항/도시/항공사 상수, 공항 코드 검증, 항공사 분류 |
| `core.file_io` | preferences/session JSON atomic write |
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
- **국내 왕복**은 API-first에서 편도 목록으로 early-return 하지 않고, 가는편/오는편 조합 경로(`domestic_flow`)를 사용한다.
- 국내 검색 URL은 공항 단위(`a:GMP`)를 유지하고, 국제선만 city map(`c:SEL`)을 쓴다.
- API 실패 또는 key 미확인 시에만 DOM fallback과 수동 모드로 내려간다.
- `INVALID_CACHE_SEARCH_KEY` 시 키 exclude 대기 후 soft reload로 1회 재시도한다.
- `manual_reason`, `api_total_count`, `fetched_pages`, `api_item_count`, `dom_seen_indices`, `dom_gap_detected`를 telemetry에 남긴다.
- API pagination은 domestic/international page cap을 넘기지 않고, cap으로 잘린 경우 `api_pages_truncated`, `api_page_cap`, `api_total_pages_estimated`를 telemetry에 남긴다.
- API 성공 이후 남아 있는 pre-wait 실패 사유는 최종 `api_failure_reason`으로 유지하지 않는다.
- 국내선 canonical `price`는 기본가이고, 혜택가는 `benefit_price`/`benefit_label`에 보존한다.
- 비교·알림·테이블 최저가 하이라이트는 `effective_flight_price`를 우선한다.
- 국내선 왕복 dedup key는 시간, 편명, API key, 혜택가/혜택 라벨을 포함해야 한다.
- 공항/수하물/잔여석 등 확장 필드는 정규화·조합·export·결과 테이블에 일관 전파한다.

## UI And Data Rules

- 검색 파라미터 공용 schema: `origin`, `dest`, `dep`, `ret`, `adults`, `cabin_class`, `is_domestic`
- `is_domestic`가 없는 구 payload는 국내선 공항 코드 기준으로 추론한다.
- `user_preferences.json`과 세션 JSON root는 `schema_version = 2`를 유지한다.
- `user_preferences.json`과 세션 JSON 저장은 `core.file_io.write_text_atomic()`을 사용한다.
- 검색 패널 복원은 국내선/국제선 모드를 먼저 맞춘 뒤 공항 코드를 적용한다.
- 자동 가격 알림 실패는 모달 대신 `last_error`, 로그, 목록 상태로 노출한다.
- 자동 가격 알림 발동 모달은 `alert_hit_modal_enabled` 설정으로 on/off 한다 (기본 on).
- 자동 가격 알림 DB 조회 실패는 worker 실행으로 이어지지 않게 중단하고 telemetry/log에 남긴다.
- CSV/Excel export는 `ui.export_helpers`의 공통 컬럼 정책을 따르고 formula-like 셀을 중립화한다.
- 다중/날짜범위 검색도 child/infant 인원을 단일 검색과 동일하게 전달한다.
- 검색 성공 후 DB 저장, 검색 로그, last-result 저장, 알림 점검 실패는 결과 렌더링을 막지 않는다.

## Packaging Rules

세 spec 파일은 새 패키지와 facade를 모두 hiddenimports에 유지해야 한다.

- `FlightBot_v2.5.spec`
- `FlightBot_Simple.spec`
- `flight_bot.spec`

필수 범위:

- `core.airports`, `core.file_io`, `core.search_params`, `core.preferences`
- `scraping.interpark.*` (`contract`, `adapter`, `urls`, `selectors`, `scripts`, `network_listener`)
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

<!-- SPECKIT-AGENT-GUIDE:START -->

## Spec Kit / Spec-Driven Development (AI 에이전트 필독)

> 이 블록은 GitHub Spec Kit 활성화 및 기능 명세 작업 결과를 AI 에이전트가 바로 쓰도록 정리한 안내입니다.
> 수정 시 마커 주석을 유지하세요. 스크립트/후속 세션이 이 구간을 갱신합니다.

### 이 저장소 상태

- **프로젝트**: `Scraping-flight-information`
- **Spec Kit 초기화**: `.specify/ 있음`
- **에이전트 스킬**: Grok=True, Claude=True, Codex/Agy(.agents)=True
- **활성 기능**: 아직 `specs/` 기능 명세 없음 — `.specify/` 만 준비된 상태

### 에이전트가 먼저 읽을 파일

1. `.specify/` 및 `.grok/skills` / `.claude/skills` / `.agents/skills` 의 `speckit-*`
2. 기능 작업 시작 시 `/speckit-specify` 로 `specs/00N-...` 생성

### 권장 워크플로 (스킬 / 슬래시 커맨드)

| 단계 | 커맨드 (Grok/Claude 등) | 산출 |
|------|-------------------------|------|
| 원칙 | `/speckit-constitution` | `.specify/memory/constitution.md` |
| 명세 | `/speckit-specify` | `specs/<id>/spec.md` |
| 계획 | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 작업 | `/speckit-tasks` | `tasks.md` |
| 구현 | `/speckit-implement` | 코드 (tasks 순서) |
| 갭점검 | `/speckit-converge` | `tasks.md` 에 Phase Convergence **append-only** |

- Codex skills 모드: `$speckit-specify` 형태일 수 있음
- 스킬 파일: `.grok/skills/speckit-*/SKILL.md`, `.claude/skills/speckit-*/SKILL.md`

### 작업 규칙 (에이전트)

1. **새 기능/큰 변경 전** 활성 `spec.md`·`tasks.md` 를 읽고, 없으면 specify→plan→tasks 순으로 만든다.
2. **구현은 tasks.md 체크리스트**를 따른다. 완료 시 `- [ ]` → `- [x]`.
3. **`/speckit-converge` 는 tasks.md 를 rewrite 하지 않는다** — 잔여 갭만 하단 Phase 로 append.
4. brownfield 프로젝트는 상당 기능이 이미 있을 수 있다. 중복 구현 전에 코드·`[x]` 태스크를 확인한다.
5. 웹/데스크톱 패리티 등 **out-of-scope Assumptions** 는 새 feature 로 분리하는 것을 선호한다.
6. 기본 integration 은 **grok** 이며, 동일 레포에 claude / codex / agy 스킬도 multi-install 되어 있을 수 있다.

### 관련 링크

- Spec Kit: https://github.com/github/spec-kit
- 로컬 CLI: `specify` (uv tool, 버전은 `specify version`)

<!-- SPECKIT-AGENT-GUIDE:END -->
