# Refactor Split Report (2026-03-02)

## 1) ?? ??
- `backups/code_snapshot_20260302_094406.zip`
- `backups/code_snapshot_20260302_094406.zip.sha256`
- `backups/code_snapshot_20260302_094406.zip.contents.txt`

## 2) ?? ?? ??
- facade ??
  - `gui_v2.py`
  - `database.py`
  - `scraper_v2.py`
  - `ui/components.py`, `ui/dialogs.py`, `ui/workers.py`
- ?? ??
  - `app/` (MainWindow + mixin)
  - `storage/` (DB ???? mixin)
  - `scraping/` (????/??/??/??)
  - `ui/*_*.py` (UI ?? ??)

## 3) .spec ?? ? ??
- ??? ??: `Analysis(["gui_v2.py"])`
- ??: `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`
- ??: ?? ??(`app/*`, `scraping/*`, `storage/*`, `ui/*_*`)? `hiddenimports`? ??

## 4) ?? ??? ??
- `README.md`: ??/????/spec ??
- `claude.md`: Refactor Update + spec ??? ?? ??
- `gemini.md`: 2026-03-02 ??? ???? ?? ??
- `IMPLEMENTATION_RISK_REVIEW_2026-03-02.md`: ????/?? ?? ?? ??

## 5) ?? ??
- import compatibility smoke ??
- `python -m py_compile` ?? ??
- `pytest -q`: `44 passed`

## 6) Follow-up (2026-03-05)
- `pytest -q`: `49 passed` (2026-03-05 구현 정합성 패치 반영 후)
- `.spec` 3종 `hiddenimports`에 facade + 분할 모듈 보강 추가
- `IMPLEMENTATION_RISK_REVIEW_2026-03-02.md` 파일은 워크트리에서 삭제 상태이며, 후속 감사 내용은 `IMPLEMENTATION_AUDIT_2026-03-05.md`에 통합 기록
