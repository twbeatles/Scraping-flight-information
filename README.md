# ✈️ Flight Bot v2.8 - Pro
**Playwright 기반 실시간 항공권 최저가 검색 및 분석 솔루션**

---

## ✨ v2.8 업데이트 (2026-01)

### 🛡️ 안정성 강화
- **커스텀 예외 클래스**: `ScraperError`, `BrowserInitError`, `NetworkError` 도입
- **컨텍스트 매니저**: `with PlaywrightScraper() as scraper:` 문법 지원
- **브라우저 초기화 개선**: Chrome → Edge → Chromium 순차 시도

### ⚡ 리소스 관리 개선
- 검색 취소 시 브라우저 안전 종료 (`cancel()` 메서드)
- 리소스 정리 순서 최적화 (page → context → browser → playwright)
- finally 블록으로 리소스 정리 보장

### 📊 로깅 개선
- 성능 메트릭 자동 로깅 (검색 소요시간, 결과 수)
- 예: `📊 검색 완료 (25.3초, 42건)`

### 🔧 코드 품질
- `PreferenceManager.export_all_settings()` / `import_settings()` 추가
- 타입 힌트 강화

---

## 🚀 주요 기능

| 카테고리 | 기능 |
|----------|------|
| **검색** | 국내선/국제선, 다중 목적지, 날짜 범위, 좌석등급 선택 |
| **필터** | 시간대, 가격 범위, 항공사 (LCC/FSC), 경유 횟수 |
| **데이터** | 세션 저장/복원, 캘린더 뷰, 즐겨찾기, Excel/CSV 내보내기 |
| **알림** | 가격 알림 설정 및 관리 |

---

## 🛠️ 설치 및 실행

### 요구사항
- Python 3.10+
- Chrome, Edge 또는 Chromium 브라우저

### 설치
```bash
pip install playwright PyQt6 openpyxl
playwright install chromium
```

### 실행
```bash
python gui_v2.py
```

---

## 📦 빌드

```bash
pip install pyinstaller
pyinstaller --clean flight_bot_v2.8.spec
```

빌드 결과: `dist/FlightBot_v2.8.exe`

> **Tip**: UPX 설치 시 추가 압축 적용 (https://github.com/upx/upx/releases)

---

## 📖 단축키

| 키 | 기능 |
|---|---|
| `Ctrl+Enter` | 검색 시작 |
| `Esc` | 검색 중단 (브라우저 안전 종료) |
| `F5` | 필터 새로고침 |
| `Ctrl+F` | 필터로 포커스 |

---

## 🗂️ 프로젝트 구조

```
├── gui_v2.py          # 메인 GUI (PyQt6)
├── scraper_v2.py      # Playwright 스크래퍼 (예외/컨텍스트 매니저)
├── config.py          # 설정 및 환경설정 관리
├── database.py        # SQLite 데이터베이스 + 가격 알림
├── flight_bot_v2.8.spec  # PyInstaller 빌드 설정
└── README.md
```

---

## 📝 변경 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|----------|
| v2.8 | 2026-01 | 예외 클래스, 컨텍스트 매니저, 취소 개선, 성능 로깅 |
| v2.7 | 2026-01 | 가격 알림, 설정 백업/복원, 테마 저장 |

---

**Disclaimer**: 개인 학습 및 연구 목적으로 제작되었습니다.
