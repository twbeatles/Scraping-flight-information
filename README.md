# ✈️ Flight Bot v2.5

**Playwright 기반 실시간 항공권 최저가 비교 분석 도구**

인터파크 항공권을 자동으로 검색하여 최저가를 찾아주는 PyQt6 기반 데스크톱 애플리케이션입니다.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Playwright](https://img.shields.io/badge/Scraper-Playwright-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 목차

1. [주요 기능](#-주요-기능)
2. [스크린샷](#-스크린샷)
3. [설치 방법](#️-설치-방법)
4. [사용 방법](#-사용-방법)
5. [고급 기능](#-고급-기능)
6. [키보드 단축키](#️-키보드-단축키)
7. [프로젝트 구조](#-프로젝트-구조)
8. [설정](#-설정)
9. [빌드 (EXE 생성)](#-빌드-exe-생성)
10. [문제 해결](#-문제-해결)
11. [변경 로그](#-변경-로그)
12. [기여](#-기여)

---

## 🌟 주요 기능

### ✨ 검색 기능
- **국내선/국제선** 항공권 검색
- **왕복/편도** 검색 지원
- **좌석 등급** 선택 (이코노미/비즈니스/일등석)
- **다중 목적지** 동시 검색 (최대 5개 목적지 비교)
- **날짜 범위** 검색으로 최저가 날짜 찾기 (최대 30일)
- **수동 모드** 자동 추출 실패 시 브라우저 유지, 수동 추출/닫기 지원 (전용 텔레메트리 이벤트 기록)

### 📊 분석 기능
- **실시간 가격 비교** (최대 1,000개 결과)
- **가격 색상 코딩** (녹색: 저가 ~20%, 노랑: 중간, 빨강: 고가 80%~)
- **캘린더뷰** - 날짜별 최저가 시각화
- **필터링** - 직항/경유, 항공사 유형(LCC/FSC), 시간대, 가격대

### 💾 관리 기능
- **즐겨찾기** - 관심 항공편 저장 및 메모
- **검색 기록** - 이전 검색 조건 복원
- **세션 저장/불러오기** - 검색 결과 JSON 파일로 저장
- **가격 알림** - 목표 가격 이하 도달 시 알림
- **자동 알림 점검(옵션)** - 앱 실행 중 주기 점검(QTimer, 기본 OFF)
- **CSV/Excel 내보내기** - 결과 파일 저장

### 🎨 UI/UX
- **모던 다크 테마** (라이트 테마 전환 가능)
- **프리미엄 그라데이션** 버튼 및 glassmorphism 효과
- **반응형 레이아웃** - 다양한 화면 크기 지원
- **키보드 단축키** 지원
- **HiDPI(고해상도)** 디스플레이 지원

---

## 📸 스크린샷

> 프로그램 실행 시 모던한 다크 테마의 인터페이스가 표시됩니다.
> - 상단: 검색 조건 입력 패널
> - 중앙: 필터 및 검색 진행 상태
> - 하단: 결과 테이블 / 즐겨찾기 / 로그 탭

---

## 🛠️ 설치 방법

### 시스템 요구 사항
- **운영체제**: Windows 10/11
- **Python**: 3.10 이상
- **브라우저**: Chrome, Edge, 또는 Chromium 중 하나

### 1단계: 저장소 클론 또는 다운로드

```bash
git clone https://github.com/twbeatles/Scraping-flight-information.git
cd Scraping-flight-information
```

### 2단계: 가상 환경 생성 (권장)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3단계: 의존성 설치

```bash
pip install -r requirements.txt
```

> `openpyxl`(Excel 입출력), `pytest`(테스트), `pyright`(정적 타입 검사)는 `requirements.txt`에 포함되어 함께 설치됩니다.

### 4단계: Playwright 브라우저 설치

```bash
playwright install chromium
```

> **참고**: Chrome이나 Edge가 이미 설치되어 있다면 자동으로 해당 브라우저를 사용합니다.

### 5단계: 실행

```bash
python gui_v2.py
```

---

## 🎯 사용 방법

### 기본 검색

1. **출발지 선택**: 드롭다운에서 출발 공항 선택 (예: ICN 인천)
2. **도착지 선택**: 드롭다운에서 도착 공항 선택 (예: NRT 나리타)
   - 직접 입력 시 **3자리 영문 코드**만 허용됩니다.
   - 🇰🇷 국내선 모드에서는 `ICN/GMP/CJU/PUS/TAE/SEL` 등 국내 코드만 허용되며, 비국내 코드는 검색이 차단됩니다.
3. **여정 유형 선택**: 
   - 왕복: 가는 날 + 오는 날 모두 선택
   - 편도: 가는 날만 선택
4. **노선 유형 선택**:
   - 🇰🇷 국내선: 국내 공항 간 이동 (서울 ↔ 제주 등)
   - ✈️ 국제선: 해외 공항 이동
5. **날짜 선택**: 캘린더에서 출발일/귀국일 선택
6. **인원 설정**: 성인 인원 수 입력 (1-9명)
7. **좌석 등급 선택**: 이코노미/비즈니스/일등석
8. **🔍 검색 버튼 클릭** 또는 `Ctrl+Enter`

### 검색 결과 활용

| 작업 | 방법 |
|------|------|
| 예약 페이지 열기 | 결과 행 **더블클릭** (현재 검색의 `cabin`/`adult` 파라미터 포함) |
| 즐겨찾기 추가 | 행 **우클릭** → "⭐ 즐겨찾기 추가" |
| 정보 복사 | 행 **우클릭** → "📋 정보 복사" |
| 정렬 | 컬럼 헤더 클릭 (가격, 시간 등) |
| 상세 보기 | 마우스 오버 시 툴팁 표시 |

### 필터 사용법

1. **직항만**: 경유 없는 노선만 표시
2. **경유 포함**: 경유 노선도 함께 표시
3. **항공사 유형**:
   - 전체: 모든 항공사
   - 🏷️ LCC: 저비용항공사 (제주항공, 진에어, 티웨이 등)
   - ✈️ FSC: 일반항공사 (대한항공, 아시아나)
4. **시간대 필터**: 
   - 가는편: 출발 시간 범위 (예: 오전 6시 ~ 오후 6시)
   - 오는편: 귀국편 출발 시간 범위
5. **가격대 필터**: 최소/최대 가격 설정 (만원 단위)
6. **최대 경유 횟수**: 허용할 최대 환승 횟수

---

## 🚀 고급 기능

### 🌍 다중 목적지 검색

여러 목적지의 가격을 한 번에 비교하려면:

1. 헤더의 **🌍 다중 목적지** 버튼 클릭
2. 출발지 선택
3. 비교할 **도착지 2~5개** 체크 (출발지와 동일 공항은 자동 제외)
4. 날짜 및 인원 설정
5. **🔍 다중 검색 시작** 클릭
6. 결과: 각 목적지별 최저가 비교표 표시

### 📅 날짜 범위 검색

가장 저렴한 출발 날짜를 찾으려면:

1. 헤더의 **📅 날짜 범위** 버튼 클릭
2. 출발지/도착지 선택
3. **검색 시작일 ~ 종료일** 설정 (예: 1월 1일 ~ 1월 15일)
4. **여행 기간** 설정 (예: 3박)
5. **🔍 날짜 검색 시작** 클릭
6. 결과: 각 날짜별 최저가 표시

> ⚠️ 날짜 범위는 **최대 30일 하드캡**입니다.
> 15~30일 구간은 실행 전 확인 메시지가 표시됩니다.

### 📆 캘린더 뷰

날짜범위 검색 후 시각적으로 최저가를 확인:

1. 먼저 **📅 날짜 범위** 검색 수행
2. 헤더의 **📆 캘린더뷰** 버튼 클릭
3. 캘린더에서 각 날짜별 가격 색상 확인:
   - 🟢 녹색: 최저가 (하위 30%)
   - 🟡 노랑: 중간 (30~60%)
   - 🔴 빨강: 고가 (상위 40%)
4. 날짜 클릭 시 해당 날짜로 검색 조건 변경

### 🔔 가격 알림

목표 가격 도달 시 알림 받기:

1. 헤더의 **🔔 가격알림** 버튼 클릭
2. **➕ 새 알림 추가** 섹션에서:
   - 출발지/도착지 선택
   - 여행 날짜 설정
   - 필요 시 **편도 알림** 체크 (귀국일 없이 감시)
   - **목표 가격** 입력 (예: 300,000원)
3. **🔔 알림 추가** 클릭
4. 수동 검색 또는 자동 점검 주기에서 목표 가격 이하 발견 시 알림

> ℹ️ v2.5 개선: 설정에서 자동 점검을 활성화하면 앱 실행 중 주기적으로 알림 조건을 확인할 수 있습니다.  
> 자동 점검은 백그라운드(헤드리스) 검색으로 동작하며 기본값은 **비활성화(OFF)** 입니다.

### 💾 세션 저장 및 불러오기

검색 결과를 파일로 저장/복원:

**저장하기:**
1. 검색 완료 후 헤더의 **💾** 버튼 클릭
2. 저장 위치 및 파일명 지정
3. JSON 파일로 저장

**불러오기:**
1. 헤더의 **📂** 버튼 클릭
2. 저장된 .json 파일 선택
3. 검색 조건 및 결과 복원

### 📊 결과 내보내기

| 형식 | 방법 |
|------|------|
| CSV | 결과 헤더의 **📥 CSV 저장** 클릭 |
| Excel | 테이블 우클릭 → **📊 Excel로 내보내기** |
| 클립보드 | 결과 헤더의 **📋 복사** 클릭 |

---

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+Enter` | 검색 시작 |
| `F5` | 결과 새로고침 (필터 재적용) |
| `Escape` | 검색 취소 / 다이얼로그 닫기 |
| `Ctrl+F` | 필터 영역으로 포커스 이동 |
| `더블클릭` | 해당 항공편 예약 페이지 열기 (`cabin`/`adult` 쿼리 포함) |

> 💡 **⌨️** 버튼을 클릭하면 단축키 목록을 볼 수 있습니다.

---

## 📁 프로젝트 구조

```text
Scraping-flight-information/
├─ gui_v2.py                  # 실행/호환 facade (python gui_v2.py)
├─ scraper_v2.py              # 스크래퍼 facade
├─ database.py                # DB facade
├─ config.py
├─ scraper_config.py
├─ requirements.txt
├─ flight_bot.spec
├─ FlightBot_v2.5.spec
├─ FlightBot_Simple.spec
├─ app/                       # 앱 엔트리 + MainWindow 조합
│  ├─ main_window.py
│  ├─ session_manager.py
│  └─ mainwindow/
│     ├─ ui_bootstrap.py
│     ├─ ui_bootstrap_sections.py
│     ├─ telemetry.py
│     ├─ auto_alert.py
│     ├─ worker_lifecycle.py
│     ├─ favorites.py
│     ├─ exports.py
│     ├─ search_single.py
│     ├─ search_multi.py
│     ├─ search_date_range.py
│     ├─ manual_mode.py
│     ├─ filtering.py
│     ├─ history.py
│     ├─ session.py
│     ├─ calendar.py
│     └─ app_lifecycle.py
├─ ui/
│  ├─ components.py           # public facade
│  ├─ components_primitives.py
│  ├─ components_filter_panel.py
│  ├─ components_result_table.py
│  ├─ components_log_viewer.py
│  ├─ components_search_panel.py
│  ├─ search_panel_widget.py
│  ├─ search_panel_build.py
│  ├─ search_panel_actions.py
│  ├─ search_panel_state.py
│  ├─ search_panel_shared.py
│  ├─ dialogs.py              # public facade
│  ├─ dialogs_base.py
│  ├─ dialogs_calendar.py
│  ├─ dialogs_combination.py
│  ├─ dialogs_search.py
│  ├─ dialogs_search_multi.py
│  ├─ dialogs_search_date_range.py
│  ├─ dialogs_search_results.py
│  ├─ dialogs_tools.py
│  ├─ dialogs_tools_shortcuts.py
│  ├─ dialogs_tools_price_alert.py
│  ├─ dialogs_tools_settings.py
│  ├─ workers.py              # public facade
│  ├─ workers_*.py
│  ├─ styles.py               # theme facade
│  ├─ styles_dark.py
│  └─ styles_light.py
├─ scraping/
│  ├─ errors.py
│  ├─ models.py
│  ├─ playwright_scraper.py   # public entrypoint wrapper
│  ├─ playwright_browser.py
│  ├─ playwright_search.py
│  ├─ playwright_domestic.py
│  ├─ playwright_results.py
│  ├─ extract_domestic.py
│  ├─ extract_international.py
│  ├─ searcher.py
│  └─ parallel.py
├─ storage/
│  ├─ models.py
│  ├─ schema.py
│  ├─ flight_database.py
│  ├─ db_favorites.py
│  ├─ db_history_logs.py
│  ├─ db_telemetry.py
│  ├─ db_alerts.py
│  └─ db_last_search.py
└─ backups/
   └─ code_snapshot_*.zip     # 코드 스냅샷 백업
```

### 모듈 역할

| 구성 요소 | 설명 |
|------|------|
| `gui_v2.py` | 실행/호환 API facade (`MainWindow`, `main`) |
| `app/main_window.py` | MainWindow 클래스와 앱 진입점 |
| `app/mainwindow/ui_bootstrap_sections.py` | 메인 윈도우 UI 섹션 조립 |
| `scraper_v2.py` | 스크래퍼 공개 API facade |
| `scraping/playwright_scraper.py` | `PlaywrightScraper` 공개 진입점 wrapper |
| `scraping/playwright_*.py` | 브라우저 초기화, 검색 orchestration, 국내선 추출, 결과 정렬 분리 구현 |
| `database.py` | DB 공개 API facade |
| `storage/*` | SQLite 스키마/영속화 로직 |
| `config.py` | 공항/설정 상수, 사용자 설정 |
| `ui/components.py` | UI 컴포넌트 facade (`FilterPanel`, `ResultTable`, `SearchPanel`) |
| `ui/components_search_panel.py` + `ui/search_panel_*.py` | SearchPanel facade + 입력/상태/액션 분리 구현 |
| `ui/dialogs.py`, `ui/dialogs_search.py`, `ui/dialogs_tools.py` | 다이얼로그 facade 레이어 |
| `ui/dialogs_search_*.py`, `ui/dialogs_tools_*.py` | 검색/도구 다이얼로그 세부 구현 |
| `ui/workers.py` | 워커 facade (`SearchWorker`, `MultiSearchWorker` 등) |
| `ui/styles.py`, `ui/styles_dark.py`, `ui/styles_light.py` | 테마 facade + 개별 테마 정의 |

> 2026-03-14 기준: 외부 import 경로는 그대로 유지하고, 길어진 구현만 내부 모듈로 분리하는 1차 구조 정리를 적용했습니다.

---

## 🔧 설정

### 사용자 설정 파일

| 모드 | user_preferences.json 위치 | flight_data.db 위치 |
|------|----------------------|---------------------|
| 개발 | `./user_preferences.json` | `./flight_data.db` |
| EXE | `%LOCALAPPDATA%/FlightBot/` | `%LOCALAPPDATA%/FlightBot/` |

### 관측성 로그 파일

| 모드 | JSONL 로그 위치 |
|------|----------------|
| 개발 | `./logs/flightbot_events.jsonl` |
| EXE | %LOCALAPPDATA%/FlightBot/logs/flightbot_events.jsonl |

- 보존 정책 기본값: telemetry_events DB 30일, JSONL 10MB x 최대 5개 롤링

### 설정 가능 항목

⚙️ **설정** 버튼에서 변경 가능:

- **최대 결과 수**: 표시할 최대 검색 결과 수 (기본: 1000)
- **선호 출발 시간**: 기본 필터 시간대 설정
- **프리셋 관리**: 자주 사용하는 공항 코드 추가
- **테마**: 다크/라이트 모드 전환
- **자동 알림 점검**: 활성화 여부 및 점검 주기(분)
- **진단 정보**: 최근 성공률/수동모드 전환률/selector health 확인
  - 수동 추출 완료/실패는 ui_manual_extract_finished 이벤트로 별도 집계

### 프리셋 공항 추가

1. 검색 패널에서 출발지/도착지 옆 **➕** 버튼 클릭
2. 3자리 공항 코드 입력 (예: HND)
3. 공항명 입력 (예: 하네다)
4. 저장 후 드롭다운에서 사용 가능

---

## 📦 빌드 (EXE 생성)

### PyInstaller 빌드

```bash
# 스펙 파일 사용 (권장)
pyinstaller --clean flight_bot.spec

# 또는 직접 빌드
pyinstaller --onedir --windowed --name FlightBot_v2.5 gui_v2.py
```

### 스펙 파일 선택 가이드

| 스펙 파일 | 용도 | 빌드 명령 |
|----------|------|----------|
| `flight_bot.spec` | 경량화/최적화된 기본 GUI 배포 | `pyinstaller --clean flight_bot.spec` |
| `FlightBot_v2.5.spec` | 표준 GUI 배포 (호환 프로필) | `pyinstaller --clean FlightBot_v2.5.spec` |
| `FlightBot_Simple.spec` | 콘솔 로그 확인용 디버그 실행파일 | `pyinstaller --clean FlightBot_Simple.spec` |

> 2026-03-15 점검 결과: 세 `.spec` 파일의 `hiddenimports`를 현재 구조에 맞게 다시 동기화했습니다. facade 경로(`database`, `scraper_v2`, `ui.components`, `ui.dialogs`, `ui.styles`, `ui.workers`)는 유지하고, 신규 분리 모듈(`app.mainwindow.ui_bootstrap_sections`, `scraping.playwright_*`, `ui.search_panel_*`, `ui.dialogs_search_*`, `ui.dialogs_tools_*`, `ui.styles_dark/light`)도 함께 포함합니다.

### 빌드 결과

- `dist/FlightBot_v2.5/` 폴더 생성
- `FlightBot_v2.5.exe` 실행 파일
- 예상 크기: 80-120MB (Playwright 포함)

### 빌드 후 필수 작업

```bash
# Chromium 브라우저 설치 (최초 1회)
playwright install chromium
```

> 또는 사용자 PC에 Chrome/Edge가 설치되어 있으면 자동 사용됩니다.

---

## ❓ 문제 해결

### "브라우저를 찾을 수 없습니다"

**해결책:**
```bash
playwright install chromium
```
또는 Chrome/Edge 설치 후 재실행

### "검색 결과 없음"

**가능한 원인:**
1. 해당 노선에 항공편이 없음
2. 네트워크 연결 문제
3. 인터파크 페이지 구조 변경

**해결책:**
- 수동 모드 전환 시 직접 브라우저에서 검색 후 데이터 추출 가능
- 수동 모드 브라우저는 유지되며 필요 시 **브라우저 닫기** 버튼으로 종료
- 다른 날짜나 노선으로 테스트

### 검색 속도가 느림

**해결책:**
- 네트워크 상태 확인
- 결과 수 제한 (설정에서 조정)
- 날짜 범위 검색 시 범위 축소

### 프로그램이 응답 없음

**해결책:**
- `Escape` 키로 검색 취소
- 작업 관리자에서 Python/Chrome 프로세스 종료 후 재시작

---

## 📝 변경 로그

### v2.5.7 (2026-03-15)
- ✅ **정적 품질 기준선 확정**
  - `pyrightconfig.json` 기준을 Python `3.10` + `typeCheckingMode=standard`로 고정
  - `PlaywrightScraper`, `SearchPanel`, `MainWindow`의 타입 계약을 정리해 Pylance/pyright 기준 `0 errors` 달성
- 🔤 **인코딩/문서 정합성 점검**
  - tracked `.md`/`.spec`/코드 파일을 다시 점검했고 실제 UTF-8 손상 파일은 발견되지 않음
  - `scripts/check_tracked_text.py`, `.gitattributes`, `.github/workflows/quality.yml`로 UTF-8/LF/정적검사/테스트를 CI에 연결
- 📦 **PyInstaller spec 재점검**
  - `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`에 `ui.styles` facade hiddenimport를 추가해 현재 공개 import 구조와 패키징 기준을 맞춤
- 🧹 **저장소 운영 점검**
  - `.gitignore`를 재확인했고, 현재 기준에서는 추가 ignore 규칙 없이도 새 품질 도구/산출물을 안전하게 커버함
- ✅ **검증**
  - `pyright` -> `0 errors`
  - `python scripts/check_tracked_text.py` -> `Checked 97 tracked text files: OK`
  - `pytest -q` -> `56 passed`

### v2.5.6 (2026-03-14)
- 🧩 **1차 코드 분할 리팩토링 마감**
  - `scraping/playwright_scraper.py`를 얇은 진입점으로 정리하고 브라우저/검색/국내선/결과 처리를 `scraping/playwright_*.py`로 분리
  - `app/mainwindow/ui_bootstrap.py`, `ui/components_search_panel.py`, `ui/dialogs_search.py`, `ui/dialogs_tools.py`, `ui/styles.py`를 facade 성격으로 정리하고 세부 구현을 전용 모듈로 분리
- 📦 **PyInstaller spec 동기화**
  - `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`에 새 분리 모듈 hiddenimports 반영
- 📚 **문서 정합성 보강**
  - README/가이드 문서/SCRAPING_AUDIT에 2026-03-14 기준 구조, 백업, 검증 현황 추가
  - 리팩토링 시작 백업: `backups/code_snapshot_20260314_231358.zip`
- ✅ **검증**
  - `python -m py_compile` 대상 파일 통과
  - `pytest -q` 기준 `56 passed`

### v2.5.5 (2026-03-09)
- ✅ **정적 타입 품질 정비**
  - 리포지토리 루트 기준 `pyright` 결과 `0 errors` 달성
  - mixin 구조/Qt Optional 경로/테스트 더미 타입을 정리해 Pylance 오탐을 제거
- 🧾 **개발 설정 추가**
  - `pyrightconfig.json` 추가 (분석 대상/제외 경로/진단 기준 고정)
  - `.editorconfig` 추가 (`utf-8`, `lf`, final newline)
  - `.vscode/settings.json` 추가 및 `.gitignore` 예외 규칙 반영
- 🔤 **문서/인코딩 정합성**
  - README/리포트 문서의 깨진 문구 복구
  - 저장소 텍스트 파일 UTF-8/BOM 정책 정규화

### v2.5.4 (2026-03-05)
- 🛠️ **구현 정합성 패치 일괄 적용**
  - `scraping/parallel.py`에 로거 정의 추가로 `ParallelSearcher` 런타임 `NameError` 제거 (public API 유지)
  - 결과 더블클릭 예약 URL에 `?cabin={...}&adult={...}` 반영
  - 검색 기록 복원을 `_restore_search_panel_from_params()` 경로로 통합하여 `cabin_class` 복원 보장
  - 국내선 모드에서 비국내 코드 수동 입력 시 검색 하드 차단
  - 설정 import 후 `search_history`를 리스트로 정규화하고 최대 20개로 trim
  - `storage/db_last_search.py`의 깨진 단독 실행 블록 제거
- 📦 **배포/문서 동기화**
  - PyInstaller `.spec` 3종 `hiddenimports` 보강 (facade + 분할 모듈 경로)
  - `.gitignore`를 런타임 산출물 기준으로 정리 (`*.json` 광역 제외 제거, `user_preferences.json`/`flight_session_*.json`/`logs/` 명시)
- ✅ **검증**
  - `pytest -q` 기준 `49 passed`

### v2.5.3 (2026-03-02)
- 📦 **PyInstaller spec 보강**
  - `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`에 분할 모듈 경로를 `hiddenimports`로 보강
- 🧱 **구조 분리 + facade 유지**
  - facade: `gui_v2.py`, `database.py`, `scraper_v2.py`, `ui/components.py`, `ui/dialogs.py`, `ui/workers.py`
  - 구현 분리: `app/`, `storage/`, `scraping/`, `ui/*_*.py`
- 🔁 **호환성 검증**
  - 기존 실행/임포트 경로(`python gui_v2.py`, facade import) 유지 확인
- 📚 **백업/문서 동기화**
  - `backups/code_snapshot_20260302_094406.zip` + SHA256/contents 메타 기록
- ✅ **검증**
  - import smoke, `python -m py_compile`, `pytest -q` (`44 passed`)

### v2.5.2 (2026-02-26)
- 🔁 **재시도 안정성 보강**
  - `PlaywrightScraper.search()` 재시도 경로를 재귀 호출에서 반복 루프로 전환
  - 재시도 사이클마다 브라우저/컨텍스트를 명시 정리하여 리소스 누적 위험 완화
- 🧭 **실행 모드 분리**
  - 단일 검색(수동 모드 가능)만 persistent context 사용
  - 다중 목적지/날짜 범위/자동 알림 점검은 `background_mode=True`(헤드리스, non-persistent)로 실행
- 🛑 **자동 알림 취소 안정성**
  - `AlertAutoCheckWorker.cancel()` 시 활성 검색기를 즉시 close하여 종료 지연 위험 감소
- ✅ **테스트 강화**
  - background 모드 전달/수동 fallback 차단/재시도 중 close/자동 알림 취소 경로 테스트 추가
  - `pytest -q` 기준 `31 passed` 확인

### v2.5.1 (2026-02-25)
- 🔁 **스크래핑 안정성 강화**
  - 네트워크/타임아웃 계열 실패에 대한 재시도 + 지수 백오프(2s, 4s, 8s) 적용
  - 결과 대기 selector 후보 다중화 및 selector health 집계 추가
- 🎯 **검색 정확도/일관성 개선**
  - 다중 목적지/날짜 범위 검색에 좌석등급(`ECONOMY/BUSINESS/FIRST`) 전달 경로 통일
  - 국내선 판별 기준을 `config.DOMESTIC_AIRPORT_CODES` 단일 소스로 통합
  - `FlightResult` 메타(`confidence`, `extraction_source`) 추가 및 세션/DB 영속화
- 🔔 **자동 알림 점검 추가**
  - 앱 실행 중 `QTimer` 기반 가격 알림 자동 점검(기본 OFF, 기본 30분) 지원
  - 알림 항목에 좌석등급 저장/매칭 추가
- 📈 **관측성/운영성 강화**
  - JSONL 이벤트 로그 + `telemetry_events` DB 요약 지표 도입
  - 설정창 진단 섹션(최근 24시간 성공률/수동모드 전환률/주요 오류/selector health) 추가
- 🧹 **종료 안정성 개선**
  - 워커 강제종료(`terminate`) 제거, `cancel -> requestInterruption -> wait` 안전 종료로 교체
  - DB 연결 종료 API(`close()`, `close_all_connections()`) 및 종료 시 정리 반영

### v2.5 (2026-01-10)
- 🛡️ **안정성 및 리소스 관리 대폭 개선** (Critical Fixes)
  - 검색 중단(Cancel) 요청 시 즉각 반응하도록 로직 개선
  - 브라우저 종료 시 리소스 누수(좀비 프로세스) 원천 차단
  - 수동 모드 종료 시 메모리 누수 수정
  
- 🔌 **구조적 개선**
  - 데이터베이스 Multi-thread 안전성 확보 (Thread-Local Connection)
  - 브라우저 초기화 오류 시 사용자 친화적 메시지 표시
  - 로깅 시스템 통합 및 최적화
  
- 🐛 **버그 수정**
  - 고가 항공권 필터링 로직 오류 수정
  - 데이터 직렬화(to_dict) 누락 필드 보완
  
- 📄 **문서화**
  - AI 가이드라인 문서 추가 (gemini.md, claude.md)
  - README.md 사용 방법 상세화

### v2.4 (2026-01-05)
- 🎨 **UI/UX 전면 리팩토링**
  - 프리미엄 그라데이션 버튼 (#667eea → #764ba2 → #f093fb)
  - 강화된 glassmorphism 카드 효과
  - 현대적인 탭/테이블 스타일
  - Empty State 처리 추가
  
- ⚡ **성능 최적화**
  - 국내선 조합 생성 확대 (150×150 = 22,500개)
  - 화면 표시 결과 증가 (500 → 1,000개)
  - 스크롤 대기 시간 40% 단축
  - SQLite WAL 모드 활성화
  - 연결 캐싱으로 DB 성능 향상

### v2.3
- Playwright 기반 스크래핑 엔진
- 국내선 왕복 조합 검색
- 수동 모드 지원

---

## ⚠️ 주의 사항

> **법적 고지**: 이 도구는 개인 사용 목적으로 제작되었습니다.

1. **인터넷 연결** 필요
2. **Chrome, Edge, 또는 Chromium** 중 하나 설치 필요
3. 검색 빈도가 높으면 인터파크에서 **일시적 차단**될 수 있음
4. 상업적 목적 사용 시 관련 **법률 및 서비스 약관** 확인 필요
5. 항공권 가격은 실시간 변동될 수 있으며, 실제 예약 가격과 다를 수 있음

---

## 📄 라이선스

MIT License

Copyright (c) 2026

---

## 🙏 기여

버그 리포트, 기능 제안, PR 환영합니다!

### 기여 방법

1. 이 저장소 Fork
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements.txt

# 코드 실행 (디버그 모드)
python gui_v2.py

# 테스트 실행
pytest -q

# 정적 타입 검사 (Pylance/pyright 기준)
pyright

# tracked text 인코딩 검사
python scripts/check_tracked_text.py
```

> 저장소에는 `.gitattributes`, `scripts/check_tracked_text.py`, `.github/workflows/quality.yml`가 포함되어 있어 UTF-8/LF 정책, `pyright`, `pytest`를 CI에서도 함께 점검합니다.

---

## 📞 지원

- **이슈 트래커**: GitHub Issues
- **문서**: 이 README 및 gemini.md, claude.md 참조

---

*Made with ❤️ for travelers*



