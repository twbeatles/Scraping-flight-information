# ✈️ Flight Bot v2.5 - AI 개발 가이드라인 (Claude)

이 문서는 Claude AI가 Flight Bot 프로젝트 작업 시 참조해야 하는 상세 기술 가이드입니다.

---

## 🎯 프로젝트 핵심 요약

| 항목 | 내용 |
|------|------|
| **목적** | 인터파크 항공권 최저가 검색 데스크톱 앱 |
| **언어** | Python 3.10+ |
| **GUI** | PyQt6 >= 6.4.0 |
| **스크래핑** | Playwright >= 1.40.0 |
| **데이터베이스** | SQLite3 (WAL 모드) |
| **대상 OS** | Windows 10/11 |

---

## 📐 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                         MainWindow (gui_v2.py)                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ SearchPanel │ │ FilterPanel │ │ ResultTable │ │  Dialogs   │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ │
└─────────┼───────────────┼───────────────┼──────────────┼────────┘
          │               │               │              │
          v               v               v              v
┌─────────────────────────────────────────────────────────────────┐
│                     Background Workers (ui/workers.py)           │
│         SearchWorker | MultiSearchWorker | DateRangeWorker       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                  FlightSearcher (scraper_v2.py)                  │
│                         PlaywrightScraper                        │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              v               v               v                  │
│         _init_browser   search()      _extract_*()              │
│         (Chrome/Edge/   국내선/       데이터 추출                 │
│          Chromium)      국제선 분기                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                   FlightDatabase (database.py)                   │
│             favorites | price_history | search_logs              │
│                   price_alerts | last_search                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 파일별 핵심 책임

### 메인 모듈

| 파일 | 책임 | 핵심 클래스/함수 | 라인 수 |
|------|------|------------------|---------|
| `gui_v2.py` | GUI 엔트리포인트, 이벤트 처리 | `MainWindow`, `SessionManager` | ~1300 |
| `scraper_v2.py` | Playwright 스크래핑 | `FlightResult`, `PlaywrightScraper`, `FlightSearcher` | ~800 |
| `scraper_config.py` | 스크래핑 설정, JS 스크립트 | `ScraperScripts`, 상수들 | ~200 |
| `database.py` | SQLite 데이터 관리 | `FlightDatabase`, 데이터클래스들 | ~700 |
| `config.py` | 설정, 공항코드 | `PreferenceManager`, `CITY_CODES_MAP` | ~400 |

### UI 모듈

| 파일 | 책임 | 핵심 클래스 | 라인 수 |
|------|------|-------------|---------|
| `ui/styles.py` | 테마 스타일시트 | `DARK_THEME`, `LIGHT_THEME` | ~400 |
| `ui/components.py` | 재사용 위젯 | `FilterPanel`, `ResultTable`, `SearchPanel` | ~1100 |
| `ui/dialogs.py` | 팝업 다이얼로그 | `CalendarViewDialog`, `MultiDestDialog` 등 | ~1100 |
| `ui/workers.py` | 백그라운드 스레드 | `SearchWorker`, `MultiSearchWorker` | ~300 |

---

## 💡 핵심 구현 패턴

### 1. 데이터클래스 사용

```python
from dataclasses import dataclass, asdict

@dataclass
class FlightResult:
    airline: str
    price: int
    currency: str = "KRW"
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""
    stops: int = 0
    flight_number: str = ""
    source: str = "Interpark"
    
    # 귀국편
    return_departure_time: str = ""
    return_arrival_time: str = ""
    return_duration: str = ""
    return_stops: int = 0
    is_round_trip: bool = False
    
    # 국내선 가격 분리
    outbound_price: int = 0
    return_price: int = 0
    return_airline: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

### 2. 컨텍스트 매니저 패턴

```python
class PlaywrightScraper:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # 예외 전파
    
    def close(self):
        """리소스 정리 순서가 중요!"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"Close error: {e}")

# 사용 예
with PlaywrightScraper() as scraper:
    results = scraper.search(...)
# 자동으로 close() 호출됨
```

### 2.1 Persistent Context 패턴

```python
profile_dir = os.path.join(os.getcwd(), "playwright_profile")
self.context = self.playwright.chromium.launch_persistent_context(
    profile_dir,
    headless=False,
    args=browser_args,
    viewport={"width": 1400, "height": 900},
    locale="ko-KR",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
```

- 수동 모드 종료 후에도 브라우저 컨텍스트를 유지
- UI의 **브라우저 닫기** 버튼 또는 앱 종료 시 명시적으로 close()

### 3. Thread-Safe 취소 패턴

```python
class SearchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    manual_mode_signal = pyqtSignal(object)
    
    def __init__(self, ...):
        super().__init__()
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self.searcher = None
    
    def cancel(self):
        """Thread-safe 취소 및 브라우저 정리"""
        with self._cancel_lock:
            self._cancelled = True
            if self.searcher:
                try:
                    self.searcher.close()
                except Exception:
                    pass
    
    def is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled
    
    def run(self):
        try:
            self.searcher = FlightSearcher()
            # 주기적으로 취소 확인
            if self.is_cancelled():
                return
            results = self.searcher.search(...)
            if not self.is_cancelled():
                self.finished.emit(results)
        except Exception as e:
            if not self.is_cancelled():
                self.error.emit(str(e))
        finally:
            if self.searcher and not self.manual_mode:
                self.searcher.close()
```

### 4. Thread-Local DB 연결

```python
class FlightDatabase:
    _local = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        """각 스레드별 독립 연결 관리"""
        if not hasattr(FlightDatabase._local, 'connections'):
            FlightDatabase._local.connections = {}
        
        conn = FlightDatabase._local.connections.get(self.db_path)
        
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            FlightDatabase._local.connections[self.db_path] = conn
        else:
            # 연결 유효성 검사
            try:
                conn.execute("SELECT 1")
            except sqlite3.ProgrammingError:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                FlightDatabase._local.connections[self.db_path] = conn
        
        return conn
```

### 5. PyQt6 시그널 패턴

```python
class FilterPanel(QFrame):
    filter_changed = pyqtSignal(dict)  # 시그널 정의
    
    def __init__(self):
        super().__init__()
        # 위젯 이벤트를 시그널 발생에 연결
        self.chk_direct.stateChanged.connect(self._emit_filter)
        self.cb_airline.currentIndexChanged.connect(self._emit_filter)
    
    def _emit_filter(self):
        filters = self.get_current_filters()
        self.filter_changed.emit(filters)

# MainWindow에서 연결
class MainWindow(QMainWindow):
    def __init__(self):
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self._apply_filter)
    
    def _apply_filter(self, filters: dict):
        # 필터 적용 로직
        ...
```

### 6. 세션 직렬화/역직렬화

```python
class SessionManager:
    @staticmethod
    def _safe_serialize(obj) -> Any:
        """객체를 JSON 직렬화 가능하도록 변환"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    @staticmethod
    def save_session(filepath: str, search_params: dict, results: list) -> bool:
        serialized_results = []
        for r in results:
            try:
                serialized = SessionManager._safe_serialize(r)
                json.dumps(serialized)  # 검증
                serialized_results.append(serialized)
            except Exception:
                continue
        
        session_data = {
            "saved_at": datetime.now().isoformat(),
            "search_params": search_params,
            "results": serialized_results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return True
    
    @staticmethod
    def load_session(filepath: str) -> Tuple[dict, list, str]:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        for r in data.get("results", []):
            flight = FlightResult(
                airline=r.get("airline", "Unknown"),
                price=r.get("price", 0),
                # ... 나머지 필드
            )
            results.append(flight)
        
        return data.get("search_params", {}), results, data.get("saved_at", "")
```

---

## 🔄 주요 워크플로우

### 단일 검색 플로우

```
MainWindow._start_search()
    │
    ├─→ 검색 파라미터 저장 (current_search_params)
    ├─→ 검색 기록 추가 (prefs.add_history)
    ├─→ UI 상태 변경 (버튼 비활성화, 프로그레스바)
    │
    └─→ SearchWorker 생성 및 시작
         │
         ├─→ FlightSearcher.search()
         │    │
         │    ├─→ PlaywrightScraper._init_browser()
         │    │    └→ Chrome → Edge → Chromium 순차 시도
         │    │
         │    ├─→ URL 생성 및 페이지 로드
         │    │
         │    └─→ 국내선/국제선 분기
         │         ├→ 국내선: _extract_domestic_flights_data()
         │         │          → 가는편 클릭 → 오는편 추출 → 조합 생성
         │         └→ 국제선: _extract_prices()
         │
         └─→ 시그널 발생
              ├→ progress.emit(msg) → MainWindow._update_progress()
              ├→ finished.emit(results) → MainWindow._search_finished()
              └→ error.emit(err) → MainWindow._search_error()

MainWindow._search_finished()
    │
    ├─→ ResultTable.update_data(results)
    ├─→ 가격 히스토리 저장 (db.add_price_history_batch)
    ├─→ 검색 로그 저장 (db.log_search)
    ├─→ 마지막 검색 결과 저장 (db.save_last_search_results)
    └─→ 필터 적용 (_apply_filter)
```

### 국내선 왕복 처리

```
1. 검색 URL 로드
   └→ /a:GMP-a:CJU-20260120/a:CJU-a:GMP-20260125

2. 가는편 화면 대기 및 추출
   └→ _extract_domestic_flights_data()
       └→ JavaScript로 항공편 데이터 추출 (최대 150개)

3. 첫 번째 가는편 클릭
   └→ ScraperScripts.get_click_flight_script() 실행
   
4. 오는편 화면 전환 대기
   └→ 최대 15초 (1초 × 15회 폴링)
   
5. 오는편 추출
   └→ _extract_domestic_flights_data() (최대 150개)

6. 조합 생성
   └→ 가는편 150 × 오는편 150 = 최대 22,500개
   
7. 결과 처리
   ├→ 중복 제거 (항공사+가격+시간 기준)
   ├→ 가격순 정렬
   └→ 상위 max_results개 반환
```

### 필터 적용 플로우

```
FilterPanel 위젯 변경
    │
    └─→ filter_changed.emit(filters)
         │
         └─→ MainWindow._apply_filter(filters)
              │
              ├─→ all_results에서 필터링
              │    ├→ 직항/경유 체크
              │    ├→ 항공사 카테고리 (config.get_airline_category)
              │    ├→ 시간대 필터 (가는편, 오는편)
              │    ├→ 가격 범위 필터
              │    └→ 최대 경유 횟수
              │
              └─→ ResultTable.update_data(filtered)
```

---

## ⚙️ 설정 및 상수

### 타임아웃 설정 (scraper_config.py)

```python
MAX_RETRY_COUNT = 3              # 최대 재시도 횟수
RETRY_DELAY_SECONDS = 2          # 재시도 대기 (초)
PAGE_LOAD_TIMEOUT_MS = 60000     # 페이지 로딩 (60초)
DATA_WAIT_TIMEOUT_SECONDS = 30   # 데이터 대기 (30초)
SCROLL_PAUSE_TIME = 1.0          # 스크롤 대기 (1초)
```

### 국내선 공항 코드

```python
DOMESTIC_AIRPORTS = {"ICN", "GMP", "CJU", "PUS", "TAE", "SEL"}
```

### 좌석 등급

```python
cabin_class: Literal["ECONOMY", "BUSINESS", "FIRST"]

# UI 표시
cabin_labels = {
    "ECONOMY": "💺 이코노미",
    "BUSINESS": "💼 비즈니스", 
    "FIRST": "👑 일등석"
}
```

### 파일 저장 위치

| 모드 | preferences.json | flight_data.db |
|------|------------------|----------------|
| 개발 | `./preferences.json` | `./flight_data.db` |
| EXE | `%LOCALAPPDATA%/FlightBot/` | `%LOCALAPPDATA%/FlightBot/` |

### 필터 상수 (gui_v2.py)

```python
MAX_PRICE_FILTER = 99_990_000  # 필터 최대값 (무제한 표시용)
```

---

## 🎨 UI 테마 시스템

### 색상 팔레트

```python
# 다크 테마 주요 색상
COLORS_DARK = {
    "bg_main": "#0a0a14",
    "bg_card": "rgba(22, 33, 62, 0.8)",
    "border_accent": "rgba(34, 211, 238, 0.2)",
    
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    
    "cyan": "#22d3ee",      # 기본 강조
    "purple": "#a78bfa",    # 보조 강조
    "green": "#22c55e",     # 성공/저가
    "red": "#ef4444",       # 경고/고가
    "orange": "#f59e0b",    # 주의
    "blue": "#4cc9f0",      # 정보
}

# 라이트 테마 주요 색상
COLORS_LIGHT = {
    "bg_main": "#f8fafc",
    "bg_card": "rgba(255, 255, 255, 0.95)",
    "border_accent": "rgba(59, 130, 246, 0.3)",
    
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
}
```

### 스타일 ID 컨벤션

```css
/* 컨테이너 */
#card                   /* 카드 패널 */

/* 버튼 */
#search_btn             /* 검색 버튼 (그라데이션) */
#secondary_btn          /* 보조 버튼 */
#filter_btn             /* 필터 토글 */
#manual_btn             /* 수동 추출 (로즈 그라데이션) */
#icon_btn               /* 아이콘 버튼 */
#tool_btn               /* 툴바 버튼 */

/* 테이블/뷰 */
#log_view               /* 로그 뷰어 */

/* 라벨 */
#title                  /* 메인 타이틀 */
#subtitle               /* 서브타이틀 */
#section_title          /* 섹션 제목 */
#price_highlight        /* 가격 강조 */

/* 구분선 */
#h_separator            /* 가로 구분선 */
#v_separator            /* 세로 구분선 */
```

### 그라데이션 정의

```css
/* 검색 버튼 (보라→핑크) */
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);

/* 수동 추출 버튼 (로즈→마젠타) */
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #f43f5e, stop:0.5 #ec4899, stop:1 #d946ef);

/* 프로그레스바 (청록→보라→핑크) */
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #06b6d4, stop:0.4 #667eea, stop:0.7 #a855f7, stop:1 #ec4899);
```

---

## 🛡️ 예외 처리 전략

### 사용자 정의 예외 계층

```python
class ScraperError(Exception):
    """기본 스크래퍼 예외"""
    pass

class BrowserInitError(ScraperError):
    """브라우저 시작 실패"""
    pass

class NetworkError(ScraperError):
    """네트워크 오류"""
    pass

class DataExtractionError(ScraperError):
    """데이터 추출 실패"""
    pass
```

### 예외 처리 패턴

```python
def _search_with_retry(self, ...):
    last_error = None
    
    for attempt in range(MAX_RETRY_COUNT):
        try:
            return self._do_search(...)
        except NetworkError as e:
            last_error = e
            logger.warning(f"네트워크 오류 (시도 {attempt + 1}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
        except DataExtractionError as e:
            # 구조 변경 가능성 - 수동 모드 전환
            raise
        except Exception as e:
            last_error = e
            logger.error(f"예상치 못한 오류: {e}", exc_info=True)
            break
    
    raise last_error or ScraperError("검색 실패")
```

### UI에서의 예외 처리

```python
def _search_error(self, err_msg: str):
    """검색 오류 처리"""
    self.search_panel.set_searching(False)
    self.progress_bar.setRange(0, 100)
    self.progress_bar.setValue(0)
    self.progress_bar.setFormat("❌ 오류 발생")
    self.log_viewer.append_log(f"❌ 오류: {err_msg}")
    
    # 사용자 친화적 메시지
    if "browser" in err_msg.lower():
        QMessageBox.critical(self, "브라우저 오류",
            "브라우저를 시작할 수 없습니다.\n\n"
            "해결 방법:\n"
            "1. Chrome 또는 Edge 설치\n"
            "2. 또는: playwright install chromium")
    else:
        QMessageBox.critical(self, "오류", f"검색 중 오류 발생:\n{err_msg}")
```

---

## 🔧 빌드 구성 (flight_bot.spec)

### 제외 목록 (경량화)

```python
excludes = [
    # 미사용 라이브러리
    'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
    'tkinter', 'unittest', 'pytest', 'IPython',
    
    # Qt 관련 불필요 모듈
    'PyQt6.QtQml', 'PyQt6.Qt3D', 'PyQt6.QtNetwork',
    'PyQt6.QtWebEngine', 'PyQt6.QtMultimedia',
]
```

### Hidden Imports

```python
hiddenimports = [
    # PyQt6 필수
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    
    # Playwright 필수
    'playwright.sync_api', 'playwright._impl',
    
    # Windows 이벤트 루프
    'asyncio', 'asyncio.windows_events',
    
    # 표준 라이브러리
    'json', 'logging', 'sqlite3', 'threading', 'csv',
]
```

### 바이너리 필터링

```python
def filter_binaries(binaries):
    """불필요한 Qt 모듈 제거"""
    exclude_patterns = [
        'qt6quick', 'qt6qml', 'qt6network', 'qt63d',
        'qt6multimedia', 'qt6webengine', 'qt6pdf',
        'qt6designer', 'qt6help', 'qt6sensors',
    ]
    return [b for b in binaries 
            if not any(p in b[0].lower() for p in exclude_patterns)]
```

### 빌드 명령

```bash
# 클린 빌드 (권장)
pyinstaller --clean flight_bot.spec

# 빌드 후 크기: 80-120MB (Playwright 포함)
```

---

## 📊 성능 최적화 가이드

### 스크래핑 최적화

| 항목 | 현재 값 | 위치 | 조정 가이드 |
|------|---------|------|-------------|
| 스크롤 대기 | 1.0초 | scraper_config.py | 0.5~1.5초 범위 권장 |
| 데이터 로딩 대기 | 3초 × 10회 | scraper_v2.py | 네트워크 상태에 따라 조정 |
| 오는편 화면 대기 | 1초 × 15회 | scraper_v2.py | 줄이면 실패율 증가 |
| 국내선 조합 수 | 150×150 | scraper_v2.py | 메모리와 결과 사이 트레이드오프 |
| 최대 스크롤 횟수 | 300회 | scraper_v2.py | 무한 스크롤 페이지 대응 |

### 데이터베이스 최적화

| 설정 | 값 | 효과 |
|------|-----|------|
| WAL 모드 | 활성화 | 동시 읽기 성능 3-5배 향상 |
| synchronous | NORMAL | 쓰기 성능 향상 (안전성 약간 감소) |
| Thread-Local 연결 | 활성화 | 스레드 안전성 확보 |
| 연결 캐싱 | 스레드별 | 연결 오버헤드 제거 |
| 인덱스 | route, date | 조회 성능 향상 |

### UI 최적화

```python
# 대량 데이터 렌더링 최적화
def update_data(self, results):
    self.setUpdatesEnabled(False)  # 렌더링 일시 중단
    self.setSortingEnabled(False)  # 정렬 비활성화
    
    # 데이터 업데이트
    ...
    
    self.setSortingEnabled(True)
    self.setUpdatesEnabled(True)   # 렌더링 재개
```

---

## 🧪 테스트 고려사항

### 모킹 포인트

```python
# 브라우저 모킹
@patch.object(PlaywrightScraper, '_init_browser')
def test_search(mock_init):
    mock_init.return_value = None
    # ...

# 데이터베이스 모킹
@patch.object(FlightDatabase, '_get_connection')
def test_db(mock_conn):
    mock_conn.return_value = sqlite3.connect(':memory:')
    # ...

# 시간 모킹
@patch('scraper_v2.time.sleep')
def test_no_delay(mock_sleep):
    mock_sleep.return_value = None
    # ...
```

### 중요 테스트 케이스

1. **국내선 왕복 검색**: 가는편/오는편 조합 로직
2. **브라우저 폴백**: Chrome → Edge → Chromium 순차 시도
3. **취소 처리**: 검색 중 cancel() 호출 시 정상 종료
4. **스레드 안전성**: 여러 스레드에서 동시 DB 접근
5. **세션 저장/복원**: JSON 직렬화/역직렬화
6. **필터 조합**: 여러 필터 동시 적용
7. **빈 결과 처리**: 검색 결과 없을 때 UI 처리
8. **대량 데이터**: 1000개 이상 결과 렌더링 성능

### 통합 테스트

```python
def test_full_search_flow():
    """전체 검색 플로우 테스트"""
    # 1. MainWindow 생성
    window = MainWindow()
    
    # 2. 검색 조건 설정
    window.search_panel.cb_origin.setCurrentText("ICN")
    window.search_panel.cb_dest.setCurrentText("NRT")
    
    # 3. 검색 시작
    window._start_search("ICN", "NRT", "20260120", "20260125", 1, "ECONOMY")
    
    # 4. 완료 대기 (또는 모킹)
    ...
    
    # 5. 결과 확인
    assert len(window.all_results) > 0
```

---

## 🚨 흔한 문제 및 해결책

### 1. "브라우저를 찾을 수 없습니다"

**원인**: Chrome/Edge/Chromium 모두 없음

**해결**:
```bash
playwright install chromium
# 또는 Chrome/Edge 설치
```

### 2. "검색 결과 없음"

**가능한 원인**:
- 해당 노선에 항공편 없음
- 네트워크 타임아웃
- 페이지 구조 변경

**해결**:
- 다른 날짜/노선 테스트
- 수동 모드 사용
- `scraper_config.py` JS 스크립트 업데이트
 - 수동 모드 브라우저는 유지되며 필요 시 **브라우저 닫기**로 종료

### 3. 스레드 크래시

**원인**: UI 스레드에서 직접 DB 접근 또는 스레드간 연결 공유

**해결**:
```python
# 항상 _get_connection() 사용
conn = self.db._get_connection()
```

### 4. 메모리 누수

**원인**: Playwright 리소스 미정리

**해결**:
```python
# finally 블록에서 항상 정리
finally:
    if self.searcher and not self.manual_mode:
        self.searcher.close()
```
 - 수동 모드 컨텍스트는 **브라우저 닫기** 버튼으로 종료

### 5. UI 멈춤

**원인**: 메인 스레드에서 장시간 작업

**해결**:
```python
# 백그라운드 워커 사용
worker = SearchWorker(...)
worker.finished.connect(self._on_finished)
worker.start()
```

---

## 📈 확장 가이드

### 새 항공사 추가

```python
# 1. scraper_v2.py - 국내선인 경우
DOMESTIC_AIRLINES = [..., '새항공사']

# 2. config.py - 분류 추가
AIRLINE_CATEGORIES["LCC"].append('새항공사')
# 또는
AIRLINE_CATEGORIES["FSC"].append('새항공사')
```

### 새 검색 소스 추가

```python
# 1. 새 스크래퍼 클래스 생성
class NewSourceScraper(PlaywrightScraper):
    def search(self, origin, dest, dep, ret, ...):
        url = self._build_url(...)  # 새 소스 URL
        self.page.goto(url)
        return self._extract_data()
    
    def _extract_data(self):
        # 새 소스에 맞는 추출 로직
        ...

# 2. FlightSearcher 수정
class FlightSearcher:
    def __init__(self):
        self.scrapers = [
            PlaywrightScraper(),   # 인터파크
            NewSourceScraper(),    # 새 소스
        ]
    
    def search(self, ...):
        all_results = []
        for scraper in self.scrapers:
            try:
                results = scraper.search(...)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"{scraper.__class__.__name__} 실패: {e}")
        return sorted(all_results, key=lambda x: x.price)
```

### 새 UI 다이얼로그 추가

```python
# 1. ui/dialogs.py - 다이얼로그 클래스 정의
class NewFeatureDialog(QDialog):
    feature_selected = pyqtSignal(str)  # 시그널 정의
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 기능")
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        # 위젯 추가
        ...
        
        btn = QPushButton("확인")
        btn.clicked.connect(self._on_confirm)
        layout.addWidget(btn)
    
    def _on_confirm(self):
        self.feature_selected.emit("result")
        self.accept()

# 2. gui_v2.py - import 및 사용
from ui.dialogs import NewFeatureDialog

def _open_new_feature(self):
    dlg = NewFeatureDialog(self)
    dlg.feature_selected.connect(self._handle_feature)
    dlg.exec()
```

### 새 필터 추가

```python
# 1. ui/components.py - FilterPanel 수정
class FilterPanel(QFrame):
    def __init__(self):
        ...
        # 새 필터 위젯 추가
        self.chk_new_filter = QCheckBox("새 필터")
        self.chk_new_filter.stateChanged.connect(self._emit_filter)
        layout.addWidget(self.chk_new_filter)
    
    def get_current_filters(self):
        return {
            ...
            "new_filter": self.chk_new_filter.isChecked(),
        }

# 2. gui_v2.py - _apply_filter 수정
def _apply_filter(self, filters):
    ...
    new_filter_enabled = filters.get("new_filter", False)
    
    for f in self.all_results:
        if new_filter_enabled:
            if not check_new_condition(f):
                continue
        filtered.append(f)
```

---

## 🔐 보안 고려사항

### 민감 데이터 처리

- 사용자 검색 기록: 로컬 SQLite에만 저장
- 설정 파일: `%LOCALAPPDATA%` 아래 저장 (EXE 모드)
- 외부 전송: 없음 (순수 로컬 애플리케이션)

### 스크래핑 윤리

```python
# User-Agent 설정 - 표준 브라우저로 위장
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...'

# 과도한 요청 방지
SCROLL_PAUSE_TIME = 1.0  # 스크롤 간 1초 대기
```

### 입력 검증

```python
def validate_airport_code(code: str) -> bool:
    """공항 코드 유효성 검사"""
    return len(code) == 3 and code.isalpha() and code.isupper()

def validate_date(date_str: str) -> bool:
    """날짜 형식 검사 (YYYYMMDD)"""
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False
```

---

## 📋 코드 스타일 가이드

### 네이밍 컨벤션

| 유형 | 스타일 | 예시 |
|------|--------|------|
| 클래스 | PascalCase | `FlightSearcher` |
| 함수/메서드 | snake_case | `_extract_prices()` |
| 상수 | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| private | 언더스코어 접두사 | `_cancelled` |
| UI 요소 | snake_case | `search_btn`, `filter_panel` |
| 시그널 | snake_case | `filter_changed`, `search_requested` |

### 타입 힌팅

```python
from typing import List, Dict, Optional, Callable, Any, Tuple

def search(
    self,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
    max_results: int = 1000,
    emit: Callable[[str], None] = None
) -> List[FlightResult]:
    ...
```

### 문서화

```python
def search(self, ...) -> List[FlightResult]:
    """항공권 검색
    
    Args:
        origin: 출발지 공항/도시 코드 (예: "ICN", "SEL")
        destination: 도착지 공항/도시 코드 (예: "NRT", "TYO")
        departure_date: 출발일 (YYYYMMDD 형식)
        return_date: 귀국일 (왕복 시, None이면 편도)
        adults: 성인 인원 (1-9)
        cabin_class: 좌석 등급 ("ECONOMY", "BUSINESS", "FIRST")
        max_results: 최대 결과 수
        emit: 진행 상황 콜백 함수
    
    Returns:
        가격순 정렬된 FlightResult 리스트
    
    Raises:
        BrowserInitError: 브라우저 시작 실패
        NetworkError: 네트워크 연결 실패
        DataExtractionError: 데이터 추출 실패
    
    Example:
        >>> searcher = FlightSearcher()
        >>> results = searcher.search("ICN", "NRT", "20260120", "20260125")
        >>> print(f"최저가: {results[0].price:,}원")
    """
```

### Import 순서

```python
# 1. 표준 라이브러리
import sys
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

# 2. 서드파티 라이브러리
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import pyqtSignal, QThread
from playwright.sync_api import sync_playwright

# 3. 로컬 모듈
from scraper_v2 import FlightSearcher, FlightResult
from database import FlightDatabase
import config
from ui.components import FilterPanel, ResultTable
```

---

## 🔗 외부 의존성

### 필수

| 패키지 | 버전 | 용도 |
|--------|------|------|
| PyQt6 | >= 6.4.0 | GUI 프레임워크 |
| playwright | >= 1.40.0 | 웹 스크래핑 |

### 선택적

| 패키지 | 용도 |
|--------|------|
| openpyxl | Excel 내보내기 |
| pyinstaller | EXE 빌드 |

### 런타임 요구사항

- Chrome, Edge, 또는 Chromium 중 하나 설치
- 인터넷 연결
- Windows 10/11

---

## 🔗 참고 URL

- **인터파크 항공 검색**: `https://travel.interpark.com/air/search/`
- **URL 형식**:
  - 왕복: `/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}/{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{ret}?cabin={cabin}&adult={adults}`
  - 편도: `/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}?cabin={cabin}&adult={adults}`
  - prefix: `c`(도시), `a`(공항)

---

*이 문서는 Flight Bot v2.5 코드베이스를 기반으로 작성되었습니다.*
*마지막 업데이트: 2026-01-15*
