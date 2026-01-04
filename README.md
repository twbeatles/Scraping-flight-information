# ✈️ Flight Bot v2.7 - Pro
**Playwright 기반 실시간 항공권 최저가 검색 및 분석 솔루션**

---

## ✨ v2.7 업데이트 (2026-01)

### 🆕 신규 기능
- **🔔 가격 알림**: 목표 가격 설정 및 알림 관리
- **🗂️ 설정 백업/복원**: 모든 설정을 JSON으로 내보내기/가져오기
- **🎨 테마 저장**: 라이트/다크 설정이 프로그램 재시작 후에도 유지

### ⚡ 성능 최적화
- 스크롤 대기 시간 50% 단축 (1.0초 → 0.5초)
- 브라우저 리소스 누수 수정 (try/finally 패턴)
- 조합 생성 최적화 (상위 50개씩만 조합)
- 안전한 파일 저장 패턴 적용
- QThread 안전 종료 패턴

### 🎨 UI/UX 개선
- 버튼 계층 구조: Primary/Secondary/Icon 스타일
- 헤더 레이아웃 그룹화 및 구분선 추가
- GroupBox/Slider/상태 레이블 스타일 강화
- 가격 강조 표시 개선

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

## 📦 빌드

```bash
pip install pyinstaller
pyinstaller --clean flight_bot.spec
```

빌드 결과: `dist/FlightBot_v2.7.exe`

> **Tip**: UPX 설치 시 추가 압축 적용 (https://github.com/upx/upx/releases)

---

## 📖 단축키

| 키 | 기능 |
|---|---|
| `Ctrl+Enter` | 검색 시작 |
| `Esc` | 검색 중단 |
| `F5` | 필터 새로고침 |
| `Ctrl+F` | 필터로 포커스 |

---

## 🗂️ 프로젝트 구조

```
├── gui_v2.py          # 메인 GUI (4300+ lines)
├── scraper_v2.py      # Playwright 스크래퍼 + ParallelSearcher
├── config.py          # 설정 및 환경설정 관리
├── database.py        # SQLite 데이터베이스 + 가격 알림
├── flight_bot.spec    # PyInstaller 빌드 설정
└── README.md
```

---

**Disclaimer**: 개인 학습 및 연구 목적으로 제작되었습니다.
