# ✈️ Flight Bot v2.4

**Playwright 기반 실시간 항공권 최저가 비교 분석 도구**

인터파크 항공권을 자동으로 검색하여 최저가를 찾아주는 PyQt6 기반 데스크톱 애플리케이션입니다.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Playwright](https://img.shields.io/badge/Scraper-Playwright-orange)

---

## 📋 주요 기능

### 🔍 검색 기능
- **국내선/국제선** 항공권 검색
- **왕복/편도** 검색 지원
- **좌석 등급** 선택 (이코노미/비즈니스/일등석)
- **다중 목적지** 동시 검색
- **날짜 범위** 검색으로 최저가 날짜 찾기

### 📊 분석 기능
- **실시간 가격 비교** (최대 1,000개 결과)
- **가격 색상 코딩** (녹색: 저가, 빨강: 고가)
- **캘린더뷰** - 날짜별 최저가 시각화
- **필터링** - 직항/경유, 항공사, 시간대, 가격대

### 💾 관리 기능
- **즐겨찾기** - 관심 항공편 저장
- **검색 기록** - 이전 검색 조건 복원
- **세션 저장/불러오기** - 검색 결과 파일 저장
- **가격 알림** - 목표 가격 설정

### 🎨 UI/UX
- **모던 다크 테마** (라이트 테마 전환 가능)
- **프리미엄 그라데이션** 버튼 및 효과
- **반응형 레이아웃**
- **키보드 단축키** 지원

---

## 🛠️ 설치 방법

### 요구 사항
- Python 3.10 이상
- Windows 10/11

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

```bash
playwright install chromium
```

### 3. 실행

```bash
python gui_v2.py
```

---

## 📦 빌드 (EXE 생성)

### PyInstaller 빌드

```bash
# 스펙 파일 사용
pyinstaller flight_bot_v2.4.spec

# 또는 직접 빌드
pyinstaller --onedir --windowed --name FlightBot_v2.4 gui_v2.py
```

### 빌드 결과
- `dist/FlightBot_v2.4/` 폴더에 실행 파일 생성
- 첫 실행 시 Chrome/Edge/Chromium 자동 탐지

---

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+Enter` | 검색 시작 |
| `F5` | 결과 새로고침 |
| `Escape` | 검색 취소 |
| `Ctrl+F` | 필터 포커스 |

---

## 📁 프로젝트 구조

```
Scraping-flight-information-main-v2/
├── gui_v2.py              # 메인 애플리케이션
├── scraper_v2.py          # Playwright 스크래퍼
├── scraper_config.py      # 스크래핑 설정
├── database.py            # SQLite 데이터베이스
├── config.py              # 공항 코드 등 설정
├── preferences.py         # 사용자 설정 관리
├── session_manager.py     # 세션 저장/불러오기
├── ui/
│   ├── styles.py          # 테마 스타일시트
│   ├── components.py      # UI 컴포넌트
│   ├── workers.py         # 백그라운드 워커
│   └── dialogs.py         # 다이얼로그
├── flight_bot_v2.4.spec   # PyInstaller 스펙
└── README.md
```

---

## 🔧 설정

### 사용자 설정 위치
- 개발 모드: `./preferences.json`
- EXE 모드: `%LOCALAPPDATA%/FlightBot/preferences.json`

### 데이터베이스 위치
- 개발 모드: `./flight_data.db`
- EXE 모드: `%LOCALAPPDATA%/FlightBot/flight_data.db`

---

## 📝 변경 로그

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

1. **인터넷 연결** 필요
2. **Chrome, Edge, 또는 Chromium** 중 하나 설치 필요
3. 검색 빈도가 높으면 **차단**될 수 있음
4. 상업적 목적 사용 시 **법적 확인** 필요

---

## 📄 라이선스

MIT License

---

## 🙏 기여

버그 리포트, 기능 제안, PR 환영합니다!
