# ✈️ Flight Bot v2.5 - AI 개발 가이드라인 (Gemini)

이 문서는 Gemini AI가 Flight Bot 프로젝트와 상호작용할 때 참조해야 하는 포괄적인 가이드라인입니다.

아래 상세 예시보다 상단의 최신 정합성 업데이트 섹션을 우선한다. 하위 섹션의 예시 코드는 개념 설명용이며 최신 구현과 일부 차이가 있을 수 있다.

---

## 📋 프로젝트 개요

### 프로젝트 정의
- **프로젝트명**: Flight Bot v2.5
- **목적**: 인터파크 항공권을 자동으로 검색하여 최저가를 찾아주는 데스크톱 애플리케이션
- **언어/버전**: Python 3.10+
- **플랫폼**: Windows 10/11
- **개발 환경**: Visual Studio Code, PyCharm
- **버전 관리**: Git

### 핵심 기술 스택
| 기술 | 버전 | 용도 |
|------|------|------|
| PyQt6 | >= 6.4.0 | GUI 프레임워크 |
| Playwright | >= 1.40.0 | 웹 스크래핑 엔진 |
| SQLite3 | 내장 | 로컬 데이터베이스 |
| PyInstaller | >= 6.0.0 | EXE 빌드 (선택사항) |
| openpyxl | 선택 | Excel 내보내기 지원 |

### 주요 기능 목록
1. **항공권 검색**: 국내선/국제선, 왕복/편도, 다양한 좌석 등급
2. **고급 필터링**: 항공사 유형, 경유 횟수, 시간대, 가격대
3. **즐겨찾기**: 관심 항공편 저장 및 관리
4. **가격 알림**: 목표 가격 설정 및 알림
5. **캘린더 뷰**: 날짜별 최저가 시각화
6. **세션 관리**: 검색 결과 저장/복원
7. **가격 히스토리**: 가격 변동 추이 분석

---

## 🔄 정합성 업데이트 (2026-03-24)

최신 코드 기준으로 아래 항목을 우선 적용한다.

1. `FlightResult`는 `confidence`, `extraction_source` 필드를 포함한다.
2. `MultiDestDialog.search_requested`/`DateRangeDialog.search_requested`는 `cabin_class`를 포함한다.
3. 자동 가격 알림은 `AlertAutoCheckWorker` + `QTimer`로 동작하며 기본값은 OFF, 30분이다.
4. 워커 종료는 `terminate()`를 사용하지 않고 `cancel() -> requestInterruption() -> wait()` 순서를 사용한다.
5. `PreferenceManager` 설정 파일명은 `user_preferences.json`이다.
6. DB는 `close()`, `close_all_connections()`, 텔레메트리 API를 제공한다.
7. 관측성은 JSONL(`logs/flightbot_events.jsonl`) + DB(`telemetry_events`) 이중 저장이다.
8. `PlaywrightScraper.search()`는 반복 루프 기반 재시도/백오프를 사용하며 시도 간 리소스를 정리한다.
9. 다중/날짜/자동알림 검색은 `background_mode=True`(헤드리스, non-persistent)로 실행한다.
10. `AlertAutoCheckWorker.cancel()`은 활성 검색기를 즉시 close한다.
11. `ParallelSearcher`는 `scraping/parallel.py` 로거 정의를 포함해 런타임 예외 없이 동작해야 하며, `scraper_v2.ParallelSearcher` 공개 경로를 유지한다.
12. 결과 더블클릭은 선택 항공편 deep link가 아니라 현재 검색 파라미터의 `cabin_class`/`adults`를 포함한 인터파크 검색 URL 재오픈이다.
13. 검색 기록 복원은 `_restore_search_panel_from_params()` 단일 복원 경로를 사용해 `cabin_class`를 포함한다.
14. 국내선 모드(`rb_domestic`)에서는 출발/도착 코드가 모두 `config.DOMESTIC_AIRPORT_CODES`에 포함되지 않으면 검색을 차단한다.
15. `PreferenceManager.import_settings()`는 병합 후 `search_history`를 리스트로 정규화하고 최대 20개로 trim한다.
16. `storage/db_last_search.py`는 mixin 모듈 전용으로 유지하며 깨진 단독 실행 블록을 두지 않는다.
17. 검색 파라미터 저장/복원 공용 규약은 `origin`, `dest`, `dep`, `ret`, `adults`, `cabin_class`, `is_domestic`다.
18. 구버전 payload에 `is_domestic`가 없으면 `config.DOMESTIC_AIRPORT_CODES` 기준으로 국내선 여부를 추론한다.
19. `user_preferences.json`과 세션 JSON 루트는 `schema_version = 2`를 사용하고, 구버전 데이터는 load/import 시 정규화한다.
20. 검색 패널 설정/프로필/세션/히스토리 복원은 `ui.search_panel_params` 공용 helper를 사용한다.
21. 설정 저장은 공항 표시 문자열이 아니라 코드(`currentData`)를 저장하며, 복원 시 국내선/국제선 모드를 먼저 맞춘 뒤 코드를 적용한다.
22. `last_search_meta`는 `is_domestic`를 저장하고, 구 row 복원 시 route 기반 추론으로 보완한다.
23. `PriceAlert` 및 `price_alerts`는 `adults`, `last_error`를 포함하며 가격 알림 매칭 기준은 `origin/dest/dep/ret/cabin_class/adults`다.
24. 자동 가격 알림 실패는 모달 대신 DB 상태(`last_error`)와 로그/목록 상태(`점검 실패`)로 노출한다.
25. PyInstaller spec 3종은 `ui.search_panel_params`를 hiddenimport에 포함해야 한다.
26. 국제선 추출은 동일 출처 API 우선(`flights/search -> status -> final POST {}`), 실패 시 DOM fallback을 사용한다.
27. 국제선 DOM fallback은 `img[alt$="로고"]`만 항공사 후보로 사용하고 `크로스셀링` alt는 버린다.
28. `FlightResult`는 `benefit_price`, `benefit_label`을 포함하며 국내선 canonical `price`는 계속 기본가다.
29. `scraping.search_sources`는 내부 source boundary이며 기본 런타임 source는 `InterparkAirSource`다.
30. `InterparkTicketSource`는 metadata + `NotImplementedError` skeleton까지만 제공한다.
31. 설정 저장은 `QSettings.sync()`까지 호출해 `SEL -> CJU` 같은 국내선 경로도 즉시 round-trip 되어야 한다.
32. 로컬/CI 정적 품질 기준선은 `pyright --warnings`다.
33. 텍스트 무결성 기준선은 `python scripts/check_tracked_text.py --check-lf`이며, UTF-8 BOM과 CRLF를 모두 실패로 취급한다.
34. 로컬 훅 기준선은 `.pre-commit-config.yaml`의 `check_tracked_text.py --check-lf` + `pyright --warnings`다.

---

## 📁 프로젝트 구조

```
Scraping-flight-information-main-v2/
├── gui_v2.py              # 메인 GUI 애플리케이션 (MainWindow 클래스)
├── scraper_v2.py          # Playwright 기반 스크래퍼 (PlaywrightScraper, FlightSearcher)
├── scraper_config.py      # 스크래핑 설정 및 JavaScript 스크립트
├── database.py            # SQLite 데이터베이스 관리 (FlightDatabase)
├── config.py              # 공항 코드, 환경설정 관리 (PreferenceManager)
├── requirements.txt       # 의존성 목록
├── flight_bot.spec        # PyInstaller 빌드 설정
├── flight_data.db         # SQLite 데이터베이스 파일
├── user_preferences.json  # 사용자 설정 파일
│
└── ui/                    # UI 컴포넌트 모듈
    ├── styles.py          # 테마 스타일시트 (DARK_THEME, LIGHT_THEME)
    ├── components.py      # 재사용 UI 컴포넌트 (FilterPanel, ResultTable, SearchPanel)
    ├── dialogs.py         # 다이얼로그 위젯 (CalendarViewDialog, MultiDestDialog 등)
    └── workers.py         # 백그라운드 스레드 워커 (SearchWorker, MultiSearchWorker)
```

- 2026-03-19 점검 결과: `.spec` 파일(`flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`)은 `hiddenimports`에 facade(`database`, `scraper_v2`, `ui.components/dialogs/workers`), 패키지 루트(`app`, `app.mainwindow`, `scraping`, `storage`), 분할 모듈(`app.mainwindow.shared`, `scraping.extract_domestic`, `scraping.extract_international`, `ui.search_panel_params`)을 함께 유지한 상태가 기준이다.

---

## 🔧 핵심 모듈 상세

### 1. `gui_v2.py` - 메인 애플리케이션

**핵심 클래스:**
- `MainWindow(QMainWindow)`: 메인 윈도우 (1280×900 최소 크기)
- `SessionManager`: 검색 세션 저장/복원 관리

**주요 기능:**
- 항공권 검색 (국내선/국제선, 왕복/편도)
- 즐겨찾기 관리
- 검색 결과 필터링 및 정렬
- CSV/Excel 내보내기
- 키보드 단축키 (Ctrl+Enter: 검색, F5: 새로고침, Escape: 취소)

**중요 상수:**
```python
MAX_PRICE_FILTER = 99_990_000  # 필터 최대값 (무제한 표시용)
```

**MainWindow 핵심 메서드:**
| 메서드 | 역할 |
|--------|------|
| `_init_ui()` | UI 레이아웃 초기화 |
| `_start_search()` | 검색 시작 |
| `_search_finished()` | 검색 완료 처리 |
| `_apply_filter()` | 필터 적용 |
| `_add_to_favorites()` | 즐겨찾기 추가 |
| `_toggle_theme()` | 테마 전환 |
| `_restore_last_search()` | 마지막 검색 복원 |
| `closeEvent()` | 종료 시 리소스 정리 |

**이벤트 시그널 연결:**
```python
# 검색 시그널
self.search_panel.search_requested.connect(self._start_search)
self.worker.progress.connect(self._update_progress)
self.worker.finished.connect(self._search_finished)
self.worker.error.connect(self._search_error)

# 필터 시그널
self.filter_panel.filter_changed.connect(self._apply_filter)

# 테이블 시그널
self.table.favorite_requested.connect(self._add_to_favorites)
self.table.cellDoubleClicked.connect(self._on_table_double_click)
```

---

### 2. `scraper_v2.py` - 스크래핑 엔진

**핵심 클래스:**
| 클래스 | 설명 |
|--------|------|
| `FlightResult` | 항공권 검색 결과 데이터클래스 |
| `PlaywrightScraper` | Playwright 기반 스크래퍼 (수동 모드 지원) |
| `FlightSearcher` | 통합 검색 엔진 (진입점) |
| `ParallelSearcher` | 병렬 다중 목적지 검색 |

**사용자 정의 예외 클래스:**
```python
class ScraperError(Exception): pass       # 기본 예외
class BrowserInitError(ScraperError): pass  # 브라우저 초기화 실패
class NetworkError(ScraperError): pass      # 네트워크 오류
class DataExtractionError(ScraperError): pass  # 데이터 추출 실패
```

**FlightResult 데이터클래스:**
```python
@dataclass
class FlightResult:
    airline: str              # 항공사명
    price: int                # 총 가격 (왕복 합산, 원)
    currency: str = "KRW"
    departure_time: str = ""  # 출발 시간 (HH:MM)
    arrival_time: str = ""    # 도착 시간 (HH:MM)
    duration: str = ""        # 비행 시간
    stops: int = 0            # 경유 횟수
    flight_number: str = ""
    source: str = "Interpark"
    
    # 귀국편 정보 (왕복 시)
    return_departure_time: str = ""
    return_arrival_time: str = ""
    return_duration: str = ""
    return_stops: int = 0
    is_round_trip: bool = False
    
    # 국내선용: 가는편/오는편 가격 분리
    outbound_price: int = 0   # 가는편 가격
    return_price: int = 0     # 오는편 가격
    return_airline: str = ""  # 오는편 항공사 (교차 항공사 시)
    benefit_price: int = 0
    benefit_label: str = ""
    confidence: float = 0.0
    extraction_source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

**브라우저 초기화 우선순위:**
1. Chrome (`channel="chrome"`)
2. Edge (`channel="msedge"`)
3. Chromium (내장, `playwright install chromium` 필요)

**Context 전략:**
- 단일 검색(수동 모드 가능): `playwright_profile` 기반 persistent context 사용
- 다중/날짜/자동알림: `background_mode=True`로 headless + non-persistent 실행
- UI의 **브라우저 닫기** 버튼 또는 앱 종료 시 정리

**국내선 공항 코드(중앙 상수):**
```python
DOMESTIC_AIRPORT_CODES = {"ICN", "GMP", "CJU", "PUS", "TAE", "SEL"}
# config.DOMESTIC_AIRPORT_CODES를 단일 소스로 사용
```

**국내선 항공사 목록:**
```python
DOMESTIC_AIRLINES = [
    '대한항공', '아시아나', '제주항공', '진에어', '티웨이',
    '에어부산', '에어서울', '이스타항공', '하이에어', '에어프레미아', '플라이강원'
]
```

**국내선 왕복 처리 로직:**
```
1. 가는편 데이터 추출 (_extract_domestic_flights_data)
   ↓
2. 첫 번째 가는편 클릭 (JavaScript)
   ↓
3. 오는편 화면 로딩 대기 (최대 15초)
   ↓
4. 오는편 데이터 추출
   ↓
5. 조합 생성 (최대 150 × 150 = 22,500개)
   ↓
6. 가격순 정렬 후 상위 max_results개 반환
```

**URL 형식:**
```python
# 왕복
f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep_date}/{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{ret_date}?cabin={cabin}&adult={adults}"

# 편도
f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep_date}?cabin={cabin}&adult={adults}"
```

---

### 3. `scraper_config.py` - 스크래핑 설정

**타임아웃 설정:**
```python
MAX_RETRY_COUNT = 3              # 최대 재시도 횟수
RETRY_DELAY_SECONDS = 2          # 재시도 간 대기 (초)
PAGE_LOAD_TIMEOUT_MS = 60000     # 페이지 로딩 타임아웃 (60초)
DATA_WAIT_TIMEOUT_SECONDS = 30   # 데이터 로딩 대기 (30초)
SCROLL_PAUSE_TIME = 1.0          # 스크롤 간 대기 (1초)
```

**정규식 패턴:**
```python
REGEX_TIME = r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})"  # 시간 추출
REGEX_PRICE = r"(\d{1,3},\d{3},?\d{0,3})\s*원"     # 가격 추출
REGEX_STOPS = r"(\d)회\s*경유"                      # 경유 횟수
```

**ScraperScripts 클래스:**
JavaScript 스크립트를 문자열로 관리하는 정적 클래스

| 메서드 | 용도 |
|--------|------|
| `get_click_flight_script(airlines)` | 항공편 클릭 |
| `get_domestic_list_script(airlines)` | 국내선 목록 추출 |
| `get_domestic_prices_script(airlines)` | 국내선 가격 추출 |
| `get_international_prices_script()` | 국제선 가격 추출 |
| `get_international_prices_fallback_script()` | 국제선 보조 추출 (구조 변경 대비) |
| `get_scroll_check_script()` | 스크롤 상태 확인 |

---

### 4. `database.py` - 데이터베이스 관리

**핵심 클래스:**
- `FlightDatabase`: Thread-safe SQLite 관리자

**데이터클래스:**
```python
@dataclass
class FavoriteItem:      # 즐겨찾기 항목
    id: int
    airline: str
    price: int
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    departure_time: str
    arrival_time: str
    stops: int
    note: str
    created_at: str
    search_params: str   # JSON 문자열

@dataclass
class PriceHistoryItem:  # 가격 히스토리
    id: int
    origin: str
    destination: str
    departure_date: str
    airline: str
    price: int
    recorded_at: str

@dataclass
class PriceAlert:        # 가격 알림
    id: int
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    target_price: int
    is_active: int
    last_checked: Optional[str]
    last_price: Optional[int]
    triggered: int
    created_at: str
    cabin_class: str = "ECONOMY"
    adults: int = 1
    last_error: str = ""
```

**데이터베이스 테이블:**
| 테이블 | 용도 | 주요 컬럼 |
|--------|------|----------|
| `favorites` | 즐겨찾기 | airline, price, origin, destination, note |
| `price_history` | 가격 변동 기록 | origin, destination, price, recorded_at |
| `search_logs` | 검색 로그 | origin, destination, result_count, min_price |
| `price_alerts` | 가격 알림 | target_price, cabin_class, adults, is_active, triggered, last_error |
| `last_search_results` | 마지막 검색 캐시 | 전체 FlightResult 필드 |
| `last_search_meta` | 마지막 검색 메타데이터 | origin, destination, searched_at, is_domestic |
| `telemetry_events` | 관측성 이벤트 | event_type, success, error_code, selector_name |

**Thread-Safety 패턴:**
```python
class FlightDatabase:
    _local = threading.local()  # Thread-Local 저장소
    
    def _get_connection(self):
        """스레드별 독립 연결 관리"""
        if not hasattr(FlightDatabase._local, 'connections'):
            FlightDatabase._local.connections = {}
        
        conn = FlightDatabase._local.connections.get(self.db_path)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            FlightDatabase._local.connections[self.db_path] = conn
        return conn
```

**주요 메서드:**
| 카테고리 | 메서드 |
|----------|--------|
| **즐겨찾기** | `add_favorite()`, `get_favorites()`, `remove_favorite()`, `is_favorite()` |
| **가격 히스토리** | `add_price_history()`, `get_price_history()`, `get_price_trend()` |
| **검색 로그** | `log_search()`, `get_popular_routes()` |
| **가격 알림** | `add_price_alert(..., cabin_class, adults)`, `get_active_alerts()`, `mark_alert_triggered()`, `update_alert_check(..., last_error)` |
| **마지막 검색** | `save_last_search_results()`, `get_last_search_results()` |
| **관측성** | `log_telemetry_event()`, `get_telemetry_summary()`, `get_selector_health()` |
| **유틸리티** | `close()`, `close_all_connections()`, `get_stats()`, `cleanup_old_data()`, `optimize()` |

---

### 5. `config.py` - 환경설정 관리

**공항 코드 매핑 (CITY_CODES_MAP):**
```python
CITY_CODES_MAP = {
    "SEL": "SEL",  # 서울 전체 (인천+김포)
    "ICN": "ICN",  # 인천
    "GMP": "GMP",  # 김포
    "CJU": "CJU",  # 제주
    "PUS": "PUS",  # 부산
    "TYO": "TYO",  # 도쿄 전체 (나리타+하네다)
    "NRT": "NRT",  # 나리타
    "HND": "HND",  # 하네다
    "OSA": "OSA",  # 오사카 전체
    "KIX": "KIX",  # 간사이
    # ... 기타 공항
}

AIRPORTS = {
    "ICN": "인천",
    "CJU": "제주",
    "NRT": "나리타",
    # ...
}
```

**항공사 분류:**
```python
AIRLINE_CATEGORIES = {
    "LCC": ["진에어", "제주항공", "티웨이항공", "에어부산", "에어서울", 
            "이스타항공", "피치항공", "스쿠트", ...],
    "FSC": ["대한항공", "아시아나항공", "일본항공", "전일본공수", ...]
}

def get_airline_category(airline: str) -> str:
    """항공사 카테고리 반환 (LCC/FSC/UNKNOWN)"""
```

**PreferenceManager 클래스:**
```python
class PreferenceManager:
    def __init__(self, filepath: str = None):
        # EXE 모드: %LOCALAPPDATA%/FlightBot/user_preferences.json
        # 개발 모드: ./user_preferences.json
    
    # 설정 관리
    def save(self) -> None
    def _load(self) -> dict
    
    # 프리셋 관리
    def add_preset(self, code: str, name: str) -> None
    def remove_preset(self, code: str) -> None
    def get_all_presets(self) -> Dict[str, str]
    
    # 검색 기록
    def add_history(self, search_info: Dict) -> None
    def get_history(self) -> List[Dict]
    
    # 프로필
    def save_profile(self, name: str, params: Dict) -> None
    def get_profile(self, name: str) -> Optional[Dict]
    def get_all_profiles(self) -> Dict[str, Dict]
    
    # 테마
    def get_theme(self) -> str  # "dark" | "light"
    def set_theme(self, theme: str) -> None
    
    # 기타 설정
    def set_max_results(self, limit: int) -> None
    def get_max_results(self) -> int
    def set_alert_auto_check(self, enabled: bool, interval_min: int) -> None
    def get_alert_auto_check(self) -> Dict[str, Any]
```

---

### 6. `ui/` 모듈

#### `ui/styles.py`
두 가지 테마 스타일시트 정의:
- `DARK_THEME`: 다크 모드 (기본)
- `LIGHT_THEME`: 라이트 모드

**색상 팔레트 (다크 테마):**
```python
# 배경색
background: #0a0a14       # 메인 배경
card_bg: rgba(22, 33, 62, 0.8)  # 카드 배경

# 강조색
cyan: #22d3ee             # 기본 강조
purple: #a78bfa           # 보조 강조
green: #22c55e            # 성공/저가
red: #ef4444              # 경고/고가
orange: #f59e0b           # 주의

# 텍스트
text_primary: #e2e8f0
text_secondary: #94a3b8
```

**주요 스타일 ID:**
| ID | 용도 |
|----|------|
| `#card` | 카드 컨테이너 |
| `#search_btn` | 검색 버튼 (그라데이션) |
| `#manual_btn` | 수동 추출 버튼 (로즈 그라데이션) |
| `#icon_btn` | 아이콘 버튼 |
| `#tool_btn` | 툴바 버튼 |
| `#secondary_btn` | 보조 버튼 |
| `#log_view` | 로그 뷰어 |
| `#v_separator` | 세로 구분선 |
| `#title` | 메인 타이틀 |
| `#subtitle` | 서브타이틀 |
| `#section_title` | 섹션 제목 |

#### `ui/components.py`

**휠 비활성화 위젯:**
스크롤 휠로 실수로 값이 변경되는 것을 방지

```python
class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class NoWheelComboBox(QComboBox): ...
class NoWheelDateEdit(QDateEdit): ...
class NoWheelTabWidget(QTabWidget): ...
```

**FilterPanel 클래스:**
| 필터 | 설명 |
|------|------|
| `chk_direct` | 직항만 체크박스 |
| `chk_layover` | 경유 포함 체크박스 |
| `cb_airline_category` | 항공사 유형 (전체/LCC/FSC) |
| `spin_max_stops` | 최대 경유 횟수 |
| `spin_start_time` / `spin_end_time` | 가는편 시간대 |
| `spin_ret_start` / `spin_ret_end` | 오는편 시간대 |
| `spin_min_price` / `spin_max_price` | 가격 범위 |

```python
class FilterPanel(QFrame):
    filter_changed = pyqtSignal(dict)  # 필터 변경 시그널
    
    def get_current_filters(self) -> dict:
        return {
            "direct_only": bool,
            "include_layover": bool,
            "airline_category": str,  # "ALL" | "LCC" | "FSC"
            "max_stops": int,
            "start_time": int,        # 0-23
            "end_time": int,          # 1-24
            "ret_start_time": int,
            "ret_end_time": int,
            "min_price": int,         # 원 단위
            "max_price": int,
        }
```

**ResultTable 클래스:**
```python
class ResultTable(QTableWidget):
    favorite_requested = pyqtSignal(int)  # 즐겨찾기 요청 시그널
    
    def update_data(self, results: List[FlightResult]) -> None:
        """결과 데이터로 테이블 갱신"""
    
    def get_flight_at_row(self, row: int) -> Optional[FlightResult]:
        """특정 행의 항공편 데이터 반환 (정렬 고려)"""
    
    def export_to_excel(self) -> None:
        """Excel 내보내기"""
    
    def export_to_csv(self) -> None:
        """CSV 내보내기"""

# 컬럼 구성
columns = ["항공사", "가격", "가는편 출발", "가는편 도착", "경유",
           "오는편 출발", "오는편 도착", "경유", "출처"]
```

**가격 색상 코딩:**
```python
ratio = (price - min_price) / price_range
if ratio < 0.2:
    color = "#22c55e"  # 녹색 - 최저가 근처
elif ratio < 0.5:
    color = "#4cc9f0"  # 청록 - 적당
elif ratio < 0.8:
    color = "#f59e0b"  # 주황 - 다소 비쌈
else:
    color = "#ef4444"  # 빨강 - 고가
```

**SearchPanel 클래스:**
```python
class SearchPanel(QFrame):
    search_requested = pyqtSignal(str, str, str, str, int, str)
    # origin, dest, dep, ret, adults, cabin_class
    
    def set_searching(self, is_searching: bool) -> None:
        """버튼 상태 토글"""
    
    def save_settings(self) -> None:
        """설정 저장"""
    
    def restore_settings(self) -> None:
        """설정 복원"""

    # 공항/도시 코드 입력 시 3자리 영문 검증 수행
```

#### `ui/dialogs.py`

| 다이얼로그 | 용도 | 주요 시그널 |
|------------|------|------------|
| `CalendarViewDialog` | 날짜별 최저가 캘린더 | `date_selected(str)` |
| `CombinationSelectorDialog` | 가는편/오는편 개별 선택 | `combination_selected(obj, obj)` |
| `MultiDestDialog` | 다중 목적지 검색 설정 | `search_requested(str, list, str, str, int, str)` |
| `DateRangeDialog` | 날짜 범위 검색 설정 | `search_requested(str, str, list, int, int, str)` |
| `MultiDestResultDialog` | 다중 목적지 결과 비교 | - |
| `DateRangeResultDialog` | 날짜별 최저가 결과 | - |
| `ShortcutsDialog` | 키보드 단축키 안내 | - |
| `PriceAlertDialog` | 가격 알림 관리 | - |
| `SettingsDialog` | 환경설정 | - |

#### `ui/workers.py`

**SearchWorker:**
```python
class SearchWorker(QThread):
    progress = pyqtSignal(str)        # 진행 메시지
    finished = pyqtSignal(list)       # 결과 리스트
    error = pyqtSignal(str)           # 오류 메시지
    manual_mode_signal = pyqtSignal(object)  # 수동 모드 전환
    
    def __init__(self, origin, dest, dep, ret, adults, cabin_class, max_results):
        self._cancelled = False
        self._cancel_lock = threading.Lock()
    
    def cancel(self):
        """Thread-safe 취소"""
        with self._cancel_lock:
            self._cancelled = True
            if hasattr(self, 'searcher') and self.searcher:
                self.searcher.close()
```

**MultiSearchWorker:**
```python
class MultiSearchWorker(QThread):
    progress = pyqtSignal(str)
    all_finished = pyqtSignal(dict)  # {dest: [FlightResult]}
```

**DateRangeWorker:**
```python
class DateRangeWorker(QThread):
    progress = pyqtSignal(str)
    all_finished = pyqtSignal(dict)  # {date: (min_price, airline)}
```

**AlertAutoCheckWorker:**
```python
class AlertAutoCheckWorker(QThread):
    progress = pyqtSignal(str)
    alert_checked = pyqtSignal(int, int)
    alert_hit = pyqtSignal(int, int, int, str, str, str)
    done = pyqtSignal(int, int)
```

- `SearchWorker`는 `background_mode=False`(수동 모드 가능), 나머지 워커는 `background_mode=True`(헤드리스) 경로를 사용한다.

---

## ⚠️ 개발 시 주의사항

### 1. 스레드 안전성
```python
# ✅ 올바른 방법: Thread-Local 연결 사용
conn = self.db._get_connection()

# ❌ 잘못된 방법: 공유 연결 사용
conn = sqlite3.connect("shared.db")  # 여러 스레드에서 사용 시 오류
```

### 2. UI 업데이트
```python
# ✅ 올바른 방법: 시그널을 통한 업데이트
self.progress.emit("검색 중...")

# ❌ 잘못된 방법: 워커 스레드에서 직접 UI 수정
self.main_window.label.setText("...")  # 크래시 발생 가능
```

### 3. 리소스 정리
```python
# Playwright 리소스 정리 순서 (중요!)
def close(self):
    if self.page:
        self.page.close()
    if self.context:
        self.context.close()
    if self.browser:
        self.browser.close()
    if self.playwright:
        self.playwright.stop()
```

### 4. 예외 처리
```python
try:
    result = scraper.search(...)
except BrowserInitError as e:
    # 브라우저 설치 안내
    QMessageBox.warning(self, "브라우저 오류", 
        "Chrome, Edge, 또는 Chromium을 설치해주세요.")
except NetworkError as e:
    # 네트워크 상태 확인 안내
    self.log_viewer.append_log(f"네트워크 오류: {e}")
except DataExtractionError as e:
    # 단일 검색은 수동 모드 전환, 백그라운드는 종료
    if background_mode:
        self.log_viewer.append_log("백그라운드 점검 종료")
    else:
        self._activate_manual_mode(searcher)
finally:
    if not manual_mode:
        searcher.close()
```

---

## 🔍 코드 수정 가이드

### 새 항공사 추가
1. `scraper_v2.py`의 `DOMESTIC_AIRLINES` 리스트에 추가 (국내선인 경우)
2. `config.py`의 `AIRLINE_CATEGORIES`에 분류 추가

```python
# scraper_v2.py
DOMESTIC_AIRLINES = [..., '새항공사']

# config.py
AIRLINE_CATEGORIES["LCC"].append('새항공사')  # 또는 FSC
```

### 새 공항 코드 추가
`config.py` 수정:
```python
CITY_CODES_MAP["NEW"] = "NEW"
AIRPORTS["NEW"] = "새공항"
```

### UI 테마 수정
`ui/styles.py`에서 해당 테마 스타일시트 수정

### 스크래핑 로직 수정
1. JavaScript 스크립트: `scraper_config.py`의 `ScraperScripts`
2. 추출 로직: `scraper_v2.py`의 `_extract_*` 메서드

### 새 다이얼로그 추가
1. `ui/dialogs.py`에 `QDialog` 서브클래스 정의
2. 필요한 시그널 정의
3. `gui_v2.py`에서 import 및 연결

---

## 📊 성능 최적화 포인트

| 항목 | 현재 값 | 위치 | 설명 |
|------|---------|------|------|
| 스크롤 대기 | 1.0초 | scraper_config.py | 값 줄이면 빠르지만 불안정 |
| 국내선 조합 수 | 150×150 | scraper_v2.py | 조합 수 줄이면 일부 결과 누락 |
| 최대 결과 수 | 1,000개 | gui_v2.py | 메모리 사용량에 영향 |
| DB WAL 모드 | 활성화 | database.py | 동시 읽기 성능 향상 |
| 연결 캐싱 | Thread-Local | database.py | 연결 오버헤드 감소 |

---

## 📝 로깅

```python
# 로거 사용 패턴
import logging
logger = logging.getLogger(__name__)

# 로깅 레벨
logger.debug("상세 디버그 정보")
logger.info("일반 정보")
logger.warning("경고 메시지")
logger.error("오류 발생", exc_info=True)
```

**메인 로깅 설정 (`gui_v2.py`):**
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
```

---

## 🔗 참고 URL

- **인터파크 항공 검색**: `https://travel.interpark.com/air/search/`
- **URL 형식 예시**:
  - 왕복: `/c:SEL-a:NRT-20260120/a:NRT-c:SEL-20260125?cabin=ECONOMY&adult=1`
  - 편도: `/c:SEL-a:NRT-20260120?cabin=ECONOMY&adult=1`

---

*이 문서는 Flight Bot v2.5 코드베이스를 기반으로 작성되었습니다.*
*마지막 업데이트: 2026-03-15*


## 리팩터링 업데이트 (2026-03-02)

대규모 분리 리팩터링 이후에도 외부 호출 경로는 facade 중심으로 유지합니다.

1. `gui_v2.py`는 facade로 유지하고 구현은 `app/main_window.py`, `app/mainwindow/*`로 분리되었습니다.
2. `scraper_v2.py`는 facade로 유지하고 구현은 `scraping/*`로 분리되었습니다.
3. `database.py`는 facade로 유지하고 구현은 `storage/*`로 분리되었습니다.
4. `ui/components.py`, `ui/dialogs.py`, `ui/workers.py`는 facade로 유지하고 구현은 `ui/*_*.py`로 분리되었습니다.
5. 실행/임포트 호환 경로를 유지합니다.
   - `python gui_v2.py`
   - `from gui_v2 import MainWindow`
   - `from database import FlightDatabase`
   - `from scraper_v2 import FlightSearcher`
6. PyInstaller spec 3종(`flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`)에 분리 경로 기반 `hiddenimports`를 반영했습니다.

---

## Implementation Update (2026-03-05)

- Runtime consistency fixes applied:
  - `ParallelSearcher` logger initialization added (`scraping/parallel.py`)
  - double-click booking URL now preserves `cabin`/`adult`
  - history restore path unified via `_restore_search_panel_from_params()` including `cabin_class`
  - domestic mode now hard-blocks non-domestic manual airport codes
  - settings import now normalizes and trims `search_history` to max 20
  - broken standalone block removed from `storage/db_last_search.py`
- Packaging/docs sync:
  - all three `.spec` files updated with facade + split-module `hiddenimports` additions
  - `.gitignore` refined to ignore runtime JSON/log artifacts explicitly without broad `*.json` exclusion
- Verification:
  - `pytest -q` -> `49 passed`

## Quality Update (2026-03-15)

### Superseding Notes
- This section supersedes older type-checking and packaging notes where they differ.
- Public runtime and import compatibility remains unchanged:
  - `python gui_v2.py`
  - `from gui_v2 import MainWindow`
  - `from database import FlightDatabase`
  - `from scraper_v2 import FlightSearcher, PlaywrightScraper`
  - `from ui.dialogs import ...`
  - `from ui.components import ...`

### Static Quality Baseline
1. `pyrightconfig.json` is now pinned to Python `3.10` with `typeCheckingMode=standard`.
2. Type contracts were tightened for `PlaywrightScraper`, split `SearchPanel` mixins, and `MainWindow`.
3. Verified baseline:
   - `pyright` -> `0 errors`
   - local `pytest -q` -> `56 passed`
   - `python scripts/check_tracked_text.py` -> tracked UTF-8 text check passed

### Packaging and Repository Hygiene
1. `flight_bot.spec`, `FlightBot_v2.5.spec`, and `FlightBot_Simple.spec` were reviewed again.
2. `hiddenimports` now explicitly include the `ui.styles` facade and package roots (`app`, `app.mainwindow`, `scraping`, `storage`) alongside existing facade and split-module imports.
3. Repository guardrails added:
   - `.gitattributes`
   - `scripts/check_tracked_text.py`
   - `.github/workflows/quality.yml`
4. GitHub Actions `Quality` now runs tracked text integrity plus `pyright`; `pytest -q` remains a local verification command because the hosted Ubuntu runner is missing `libEGL.so.1` for the PyQt bootstrap.
5. `.gitignore` was reviewed after the quality-tooling update and no additional ignore entries were needed.

## Refactor Update (2026-03-14)

### Superseding Notes
- This section supersedes older split/package notes where they differ.
- Public runtime and import compatibility remains unchanged:
  - `python gui_v2.py`
  - `from gui_v2 import MainWindow`
  - `from database import FlightDatabase`
  - `from scraper_v2 import FlightSearcher, PlaywrightScraper`
  - `from ui.dialogs import ...`
  - `from ui.components import ...`

### Newly Split Internal Modules
1. `app/mainwindow/ui_bootstrap_sections.py`
2. `scraping/playwright_browser.py`
3. `scraping/playwright_search.py`
4. `scraping/playwright_domestic.py`
5. `scraping/playwright_results.py`
6. `ui/search_panel_shared.py`
7. `ui/search_panel_build.py`
8. `ui/search_panel_actions.py`
9. `ui/search_panel_state.py`
10. `ui/search_panel_widget.py`
11. `ui/dialogs_search_multi.py`
12. `ui/dialogs_search_date_range.py`
13. `ui/dialogs_search_results.py`
14. `ui/dialogs_tools_shortcuts.py`
15. `ui/dialogs_tools_price_alert.py`
16. `ui/dialogs_tools_settings.py`
17. `ui/styles_dark.py`
18. `ui/styles_light.py`

### Spec Sync
- `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec` now include second-stage split hiddenimports.
- The required hiddenimport groups are:
  - `app.mainwindow.ui_bootstrap_sections`
  - `scraping.playwright_*`
  - `ui.search_panel_*`
  - `ui.dialogs_search_*`
  - `ui.dialogs_tools_*`
  - `ui.styles_dark`, `ui.styles_light`

### Verification
- Backup created before the refactor:
  - `backups/code_snapshot_20260314_231358.zip`
  - `backups/code_snapshot_20260314_231358.zip.sha256`
  - `backups/code_snapshot_20260314_231358.zip.contents.txt`
- Validation baseline:
  - `python -m py_compile` passed
  - `pytest -q` -> `56 passed`
