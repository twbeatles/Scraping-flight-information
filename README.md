# Flight Bot V3.0 (Refactored)

네이버 항공권 검색을 자동화하고, 결과를 비교/분석할 수 있는 고급 봇입니다. (Python, PyQt6, Playwright 기반)

## 🚀 주요 기능

### 1. 강력한 검색 기능
- **다중 목적지 검색**: 한 번에 여러 도시(예: 도쿄, 오사카, 후쿠오카)를 선택하여 최저가를 비교할 수 있습니다.
- **날짜 범위 검색**: 특정 기간(예: 1월 1일 ~ 1월 30일) 내에서 가장 저렴한 출발/귀국 날짜 조합을 찾아줍니다.
- **실시간 검색**: Playwright를 이용해 실제 네이버 항공권 데이터를 실시간으로 가져옵니다.

### 2. 사용자 편의성
- **다크 모드 UI**: 눈이 편안한 현대적인 다크 테마 (Glassmorphism 적용).
- **가격 알림**: 원하는 노선과 목표 가격을 설정하면, 해당 가격 이하일 때 알림을 받을 수 있습니다.
- **즐겨찾기 및 히스토리**: 검색 결과를 저장하고, 과거 가격 추이를 확인할 수 있습니다.
- **엑셀 내보내기**: 검색 결과를 엑셀 파일로 저장하여 2차 분석이 가능합니다 (OpenPyXL 필요).

### 3. 기술적 개선 (V3.0 Refactor)
- **모듈화된 구조**: `ui`, `scraper`, `database`가 분리되어 유지보수성이 향상되었습니다.
- **설정 중앙화**: `scraper_config.py`에서 검색 로직과 패턴을 관리합니다.
- **경량화**: 불필요한 라이브러리를 제외하 최적화된 빌드를 지원합니다.

## 🛠 설치 및 실행

### 필수 요구사항
- Python 3.9 이상
- Chrome 브라우저 (Playwright 용)

### 설치 방법

1. **저장소 클론 또는 다운로드**
   ```bash
   git clone https://github.com/your-repo/flight-bot.git
   cd flight-bot
   ```

2. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```
   *(필수 라이브러리: `PyQt6`, `playwright`, `openpyxl`)*

3. **Playwright 브라우저 설치**
   ```bash
   playwright install chromium
   ```

### 실행 방법

```bash
python gui_v2.py
```

## 📦 패키징 (EXE 만들기)

PyInstaller를 사용하여 단일 실행 파일로 만들 수 있습니다. 
최적화된 `.spec` 파일이 포함되어 있습니다.

```bash
pyinstaller flight_bot_v3.0.spec
```
빌드가 완료되면 `dist/FlightBot_v3.0/` 폴더에 실행 파일이 생성됩니다.

## 📂 프로젝트 구조

```text
flight-bot/
├── gui_v2.py            # 메인 실행 파일 (GUI 진입점)
├── scraper_v2.py        # 항공권 검색 로직 (Playwright)
├── scraper_config.py    # 스크래퍼 설정 및 JS 템플릿
├── database.py          # SQLite 데이터베이스 관리
├── config.py            # 공항 코드 및 사용자 설정
├── ui/                  # UI 컴포넌트 패키지
│   ├── dialogs.py       # 각종 다이얼로그 (설정, 검색 등)
│   ├── components.py    # 커스텀 위젯 (테이블, 패널 등)
│   ├── workers.py       # 백그라운드 작업 스레드
│   └── styles.py        # CSS 스타일시트 (테마)
└── flight_bot_v3.0.spec # PyInstaller 빌드 설정
```

## ⚠️ 주의사항
- 이 프로그램은 개인적인 학습 및 연구 목적으로 제작되었습니다.
- 포털 사이트의 이용 약관을 준수하며 과도한 트래픽을 유발하지 않도록 주의하세요.
