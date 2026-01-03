# ✈️ Flight Bot v2.6 - Pro
**Playwright 기반 실시간 항공권 최저가 검색 및 분석 솔루션**

Flight Bot은 인터파크 투어의 실시간 데이터를 기반으로 최저가 항공권을 자동으로 검색, 수집, 분석하는 파이썬 데스크톱 애플리케이션입니다.

---

## ✨ v2.6 주요 업데이트 (2026-01)

### 🆕 신규 기능
- **📅 캘린더 뷰**: 날짜별 최저가를 색상 그라데이션으로 시각화
- **💺 좌석등급 검색**: 이코노미/비즈니스/일등석 선택 가능
- **💾 세션 저장/복원**: 검색 결과를 JSON으로 저장 및 불러오기
- **🎯 고급 필터**: 가격 범위 필터 (만원 단위)
- **⚡ 병렬 검색**: 다중 목적지/날짜 동시 검색 (최대 4개)
- **🔀 조합 선택기**: 가는편/오는편 개별 선택 UI

### 🎨 UI/UX 개선
- **Glassmorphism**: 반투명 카드 효과
- **3색 그라데이션**: 버튼 및 진행바 현대화
- **글로우 효과**: 입력 포커스 및 버튼 호버
- **향상된 테마**: 더 어두운 배경, 시안 악센트

### 🐛 코드 품질
- 예외 처리 강화 (모든 `except` 패턴에 로깅 추가)
- 로깅 시스템 통일 (`gui_v2.py`, `database.py`)
- 미사용 코드 정리

---

## 🚀 주요 기능

### 검색 기능
- **국내선/국제선**: 편도 및 왕복 검색
- **다중 목적지 검색**: 여러 도시 동시 비교
- **날짜 범위 검색**: 최저가 날짜 자동 탐색
- **좌석등급 선택**: ECONOMY / BUSINESS / FIRST
- **수동 모드**: 자동화 탐지 시 수동 개입 가능

### 필터 및 정렬
- **시간대 필터**: 출발/귀국 시간 범위 설정
- **가격 범위 필터**: 최소/최대 가격 설정
- **항공사 필터**: LCC/FSC 구분
- **경유 횟수**: 직항/경유 선택

### 데이터 관리
- **세션 저장/복원**: 검색 결과 JSON 파일로 저장
- **캘린더 뷰**: 날짜별 가격 시각화
- **즐겨찾기**: 항공편 저장 및 관리
- **결과 내보내기**: CSV/Excel 저장

---

## 🛠️ 설치 및 실행

### 요구사항
- Python 3.10+
- Chrome 또는 Edge 브라우저

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

## 📖 단축키

| 키 | 기능 |
|---|---|
| `Ctrl+Enter` | 검색 시작 |
| `Esc` | 검색 중단 |
| `F5` | 필터 새로고침 |
| `Ctrl+F` | 필터로 포커스 |

---

## 📦 빌드

```bash
pip install pyinstaller
pyinstaller flight_bot.spec
```

빌드 결과: `dist/FlightBot_v2.6.exe`

---

## 🗂️ 프로젝트 구조

```
├── gui_v2.py          # 메인 GUI (3750+ lines)
├── scraper_v2.py      # Playwright 스크래퍼 + ParallelSearcher
├── config.py          # 설정 및 환경설정 관리
├── database.py        # SQLite 데이터베이스
├── flight_bot.spec    # PyInstaller 빌드 설정
└── README.md
```

---

## 🆕 v2.6 클래스 추가

| 클래스 | 설명 |
|--------|------|
| `SessionManager` | 세션 저장/복원 관리 |
| `CalendarViewDialog` | 날짜별 가격 캘린더 UI |
| `CombinationSelectorDialog` | 가는편/오는편 조합 선택 |
| `ParallelSearcher` | 병렬 검색 엔진 |

---

**Disclaimer**: 개인 학습 및 연구 목적으로 제작되었습니다.
