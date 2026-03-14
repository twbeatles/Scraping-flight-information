"""Main window composition module."""

from app.mainwindow.shared import *
from typing import Any

from app.session_manager import SessionManager
from app.mainwindow.ui_bootstrap import UiBootstrapMixin
from app.mainwindow.telemetry import TelemetryMixin
from app.mainwindow.auto_alert import AutoAlertMixin
from app.mainwindow.worker_lifecycle import WorkerLifecycleMixin
from app.mainwindow.favorites import FavoritesMixin
from app.mainwindow.exports import ExportsMixin
from app.mainwindow.search_single import SearchSingleMixin
from app.mainwindow.search_multi import SearchMultiMixin
from app.mainwindow.search_date_range import SearchDateRangeMixin
from app.mainwindow.manual_mode import ManualModeMixin
from app.mainwindow.filtering import FilteringMixin
from app.mainwindow.history import HistoryMixin
from app.mainwindow.session import SessionMixin
from app.mainwindow.calendar import CalendarMixin
from app.mainwindow.app_lifecycle import AppLifecycleMixin


class MainWindow(
    QMainWindow,
    UiBootstrapMixin,
    TelemetryMixin,
    AutoAlertMixin,
    WorkerLifecycleMixin,
    FavoritesMixin,
    ExportsMixin,
    SearchSingleMixin,
    SearchMultiMixin,
    SearchDateRangeMixin,
    ManualModeMixin,
    FilteringMixin,
    HistoryMixin,
    SessionMixin,
    CalendarMixin,
    AppLifecycleMixin,
):
    prefs: config.PreferenceManager
    worker: SearchWorker | None
    multi_worker: MultiSearchWorker | None
    date_worker: DateRangeWorker | None
    alert_worker: AlertAutoCheckWorker | None
    active_searcher: FlightSearcher | None
    results: list[FlightResult]
    all_results: list[FlightResult]
    current_search_params: dict[str, Any]
    search_panel: SearchPanel
    filter_panel: FilterPanel
    table: ResultTable
    log_viewer: LogViewer
    progress_bar: QProgressBar
    tabs: QTabWidget
    favorites_tab: QWidget
    history_list: QWidget
    manual_frame: QFrame
    manual_status_label: QLabel
    btn_theme: QPushButton
    btn_toggle_search: QPushButton

    def __init__(self):
        super().__init__()
        self.setWindowTitle("✈️ Flight Bot v2.5 - Pro")
        self.setMinimumSize(1280, 900)
        
        # 테마 초기화 - 저장된 설정에서 로드
        self.prefs = config.PreferenceManager()
        saved_theme = self.prefs.get_theme()
        self.is_dark_theme = (saved_theme == "dark")
        self.setStyleSheet(DARK_THEME if self.is_dark_theme else LIGHT_THEME)
        
        self.worker = None
        self.multi_worker = None
        self.date_worker = None
        self.alert_worker = None
        self.active_searcher = None
        self.results = []
        self.all_results = []
        self.current_search_params = {}
        self._cancelling = False  # 검색 취소 중복 방지 플래그
        self._pending_filter = None
        self._last_filter_log_msg = ""
        self._last_filter_log_ts = 0.0
        self._filter_apply_timer = QTimer(self)
        self._filter_apply_timer.setSingleShot(True)
        self._filter_apply_timer.timeout.connect(self._run_scheduled_filter_apply)
        self._alert_auto_timer = QTimer(self)
        self._alert_auto_timer.setSingleShot(False)
        self._alert_auto_timer.timeout.connect(self._run_auto_alert_check)
        
        # prefs는 이미 테마 로드 시 초기화됨
        self.db = FlightDatabase()
        self.db.cleanup_old_data(days=60, telemetry_days=30)
        
        self._init_ui()
        self.search_panel.restore_settings()
        self._setup_shortcuts()
        self._configure_alert_auto_timer()
        
        # 프로그램 시작 시 마지막 검색 결과 복원
        QTimer.singleShot(0, self._restore_last_search)

MAX_PRICE_FILTER = 99_990_000

def main():
    # 로깅 설정 (중앙 집중식)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # HiDPI 설정
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
