
"""
Flight Scraper V2 - Playwright + Manual Mode
Uses Playwright for scraping with manual fallback when auto-extraction fails.
"""

import time
import os
import sys
import heapq
import threading
from collections import OrderedDict
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Callable
import logging
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

import config
import scraper_config 
from scraper_config import ScraperScripts

# 로거 설정 (중복 핸들러 방지)
logger = logging.getLogger("ScraperV2")


# === 사용자 정의 예외 클래스 ===

class ScraperError(Exception):
    """스크래퍼 기본 예외"""
    pass

class BrowserInitError(ScraperError):
    """브라우저 초기화 실패"""
    def __init__(self, message: str = "브라우저를 시작할 수 없습니다."):
        self.message = message
        super().__init__(self.message)

class NetworkError(ScraperError):
    """네트워크 연결 오류"""
    def __init__(self, message: str = "네트워크 연결에 실패했습니다.", url: str = ""):
        self.message = message
        self.url = url
        super().__init__(f"{self.message} (URL: {url})" if url else self.message)

class DataExtractionError(ScraperError):
    """데이터 추출 실패"""
    def __init__(self, message: str = "항공편 데이터를 추출할 수 없습니다."):
        self.message = message
        super().__init__(self.message)


class ManualModeActivationError(ScraperError):
    """자동 추출 실패 후 수동 모드 활성화까지 실패"""
    def __init__(self, message: str = "수동 모드로 전환하지 못했습니다."):
        self.message = message
        super().__init__(self.message)


@dataclass
class FlightResult:
    """항공권 검색 결과"""
    airline: str
    price: int  # 총 가격 (왕복 합산)
    currency: str = "KRW"
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""
    stops: int = 0
    flight_number: str = ""
    source: str = "Interpark"
    # 귀국편 정보 (왕복인 경우)
    return_departure_time: str = ""
    return_arrival_time: str = ""
    return_duration: str = ""
    return_stops: int = 0
    is_round_trip: bool = False
    # 국내선용: 가는편/오는편 가격 분리
    outbound_price: int = 0
    return_price: int = 0
    return_airline: str = ""  # 오는편 항공사 (국내선 등 교차 항공사 시)

    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlaywrightScraper:
    """Playwright 기반 스크래퍼 - 수동 모드 지원
    
    컨텍스트 매니저로 사용 가능:
        with PlaywrightScraper() as scraper:
            results = scraper.search(...)
    """
    
    # 국내선 항공사 목록 (중앙 관리)
    DOMESTIC_AIRLINES = [
        '대한항공', '아시아나', '제주항공', '진에어', '티웨이',
        '에어부산', '에어서울', '이스타항공', '하이에어', '에어프레미아', '플라이강원'
    ]
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.manual_mode = False
        self._last_is_domestic = False
        # 스크롤 추적용 인스턴스 변수 초기화
        self._no_scroll_count = 0
        self._no_new_count = 0
        self._bottom_count = 0
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 리소스 자동 정리"""
        self.close()
        return False  # 예외는 전파
    
    def _init_browser(
        self,
        log_func: Callable[[str], None] = None,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        block_resources: bool = False,
    ) -> None:
        """브라우저 초기화 (Chrome > Edge > Chromium 순서 시도)
        
        Raises:
            BrowserInitError: 모든 브라우저 시작에 실패할 경우
        """
        def log(msg):
            if log_func:
                log_func(msg)
            logger.info(msg)
        
        log("🌐 Playwright 브라우저 시작 중...")
        
        # Playwright 드라이버 초기화
        try:
            self.playwright = sync_playwright().start()
        except FileNotFoundError as e:
            error_msg = (
                "❌ Playwright 드라이버를 찾을 수 없습니다.\n\n"
                "해결 방법:\n"
                "1. 명령 프롬프트에서 실행: pip install playwright\n"
                "2. 그 후 실행: playwright install\n\n"
                f"상세 오류: {e}"
            )
            logger.error(error_msg)
            raise BrowserInitError(error_msg)
        except Exception as e:
            error_msg = (
                f"❌ Playwright 초기화에 실패했습니다.\n\n"
                f"오류: {e}\n\n"
                "해결 방법:\n"
                "- playwright 패키지 재설치: pip install --upgrade playwright"
            )
            logger.error(error_msg)
            raise BrowserInitError(error_msg)
        
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
        
        browsers_to_try = [
            ("Chrome", "chrome"),
            ("Edge", "msedge"),
            ("Chromium (내장)", None)
        ]
        
        last_error = None
        tried_browsers = []
        
        for browser_name, channel in browsers_to_try:
            try:
                log(f"  → {browser_name} 시도 중...")
                launch_options = {
                    "headless": bool(headless),
                    "args": browser_args
                }
                if channel:
                    launch_options["channel"] = channel

                if user_data_dir:
                    context_options = {
                        **launch_options,
                        "viewport": {"width": 1400, "height": 900},
                        "locale": "ko-KR",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    self.context = self.playwright.chromium.launch_persistent_context(
                        user_data_dir, **context_options
                    )
                    self._configure_resource_blocking(block_resources)
                    log(f"  ✅ {browser_name} 시작 성공 (Persistent Context)")
                else:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    log(f"  ✅ {browser_name} 시작 성공")
                return  # 성공시 반환
            except Exception as e:
                last_error = e
                tried_browsers.append(f"{browser_name}: {str(e)[:50]}")
                logger.debug(f"{browser_name} 시작 실패: {e}")
                continue
        
        # 모든 브라우저 시작 실패 - 상세 안내 메시지
        self.close()
        
        error_details = "\n".join(f"  • {b}" for b in tried_browsers)
        error_msg = (
            "❌ 사용 가능한 브라우저를 찾을 수 없습니다.\n\n"
            "📋 시도한 브라우저:\n"
            f"{error_details}\n\n"
            "💡 해결 방법 (택 1):\n"
            "  1. Chrome 설치: https://www.google.com/chrome\n"
            "  2. Edge 설치: https://www.microsoft.com/edge\n"
            "  3. 또는 명령 프롬프트에서: playwright install chromium\n\n"
            "※ Windows 10 이상에는 Edge가 기본 설치되어 있습니다.\n"
            "   Edge가 있는데도 오류가 발생하면 Edge를 최신 버전으로 업데이트하세요."
        )
        logger.error(error_msg)
        raise BrowserInitError(error_msg)

    def _configure_resource_blocking(self, enabled: bool) -> None:
        """자동(headless) 검색에서 불필요 리소스 요청을 차단한다."""
        if not enabled or not self.context:
            return

        blocked = set(getattr(scraper_config, "AUTO_BLOCK_RESOURCE_TYPES", ()))
        if not blocked:
            return

        def _route_handler(route, request):
            try:
                if request.resource_type in blocked:
                    route.abort()
                else:
                    route.continue_()
            except Exception:
                try:
                    route.continue_()
                except Exception:
                    pass

        try:
            self.context.route("**/*", _route_handler)
        except Exception as e:
            logger.debug(f"리소스 차단 라우트 설정 실패 (무시됨): {e}")

    def _enter_manual_mode(
        self,
        url: str,
        profile_dir: str,
        is_domestic: bool,
        log_func: Callable[[str], None],
        reopen_visible: bool,
    ) -> bool:
        """수동 모드 활성화. headless 자동 검색인 경우 visible 브라우저로 재오픈."""
        if not reopen_visible and self.page is not None:
            self.manual_mode = True
            log_func("🖐️ 수동 모드 활성화 - 브라우저에서 결과 로딩 후 '추출' 버튼을 누르세요")
            return True

        if reopen_visible:
            log_func("🖐️ 자동 추출 실패 - 수동 모드 브라우저를 여는 중...")
        else:
            log_func("🖐️ 수동 모드 재초기화: 기존 브라우저 세션이 없어 새로 엽니다.")
        try:
            if reopen_visible or self.page is None:
                self.close()
                self._init_browser(
                    log_func=log_func,
                    user_data_dir=profile_dir,
                    headless=False,
                    block_resources=False,
                )
                if self.context is None and self.browser is not None:
                    self.context = self.browser.new_context(
                        viewport={"width": 1400, "height": 900},
                        locale="ko-KR",
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    )
                self.page = self.context.new_page()

            if url:
                try:
                    self.page.goto(url, wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
                except PlaywrightTimeoutError:
                    log_func("⚠️ 수동 모드 페이지 로딩 시간 초과 - 계속 진행합니다.")
                except Exception as e:
                    log_func(f"⚠️ 수동 모드 페이지 진입 실패: {e}")
            self._wait_for_results(is_domestic, lambda _msg: None)
            self.manual_mode = True
            log_func("🖐️ 수동 모드 활성화 - 브라우저에서 결과 로딩 후 '추출' 버튼을 누르세요")
            return True
        except Exception as e:
            logger.error(f"수동 모드 전환 실패: {e}", exc_info=True)
            self.close()
            self.manual_mode = False
            return False

    def _wait_for_results(self, is_domestic: bool, log_func: Callable[[str], None]) -> bool:
        if not self.page:
            return False
        timeout_ms = int(scraper_config.DATA_WAIT_TIMEOUT_SECONDS * 1000)
        if is_domestic:
            selectors = [
                "button:has-text(\"원\")",
                "text=/\\d{1,3}(,\\d{3})+\\s*원/"
            ]
        else:
            selectors = [
                "li[data-index]",
                "text=/\\d{1,3}(,\\d{3})+\\s*원/"
            ]
        per_timeout = max(1000, timeout_ms // max(len(selectors), 1))
        for selector in selectors:
            try:
                self.page.wait_for_selector(selector, timeout=per_timeout)
                return True
            except PlaywrightTimeoutError:
                if log_func:
                    log_func(f"⚠️ 결과 대기 실패: {selector}")
                continue
        return False

    def _wait_for_domestic_return_view(self) -> bool:
        """국내선 왕복에서 오는편 화면 전환을 wait_for_function 기반으로 확인."""
        if not self.page:
            return False
        timeout_ms = int(max(5, scraper_config.DOMESTIC_RETURN_WAIT_TIMEOUT_SECONDS) * 1000)
        try:
            self.page.wait_for_function(
                """
                () => {
                    const bodyText = document.body?.innerText || '';
                    const priceNodes = document.querySelectorAll('button, li, span');
                    let priceCount = 0;
                    for (const node of priceNodes) {
                        const text = node.textContent || '';
                        if (/\\d{1,3}(,\\d{3})+\\s*원/.test(text)) {
                            priceCount += 1;
                            if (priceCount >= 5) break;
                        }
                    }
                    return bodyText.includes('오는편') && priceCount >= 5;
                }
                """,
                timeout=timeout_ms,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    @staticmethod
    def _sort_and_limit_results(
        results: List[FlightResult],
        max_results: int,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> List[FlightResult]:
        if not results:
            return []
        ordered = sorted(results, key=lambda x: x.price if x.price > 0 else float("inf"))
        if isinstance(max_results, int) and max_results > 0 and len(ordered) > max_results:
            if log_func:
                log_func(f"⚠️ 결과 {len(ordered)}개 중 상위 {max_results}개만 유지합니다.")
            return ordered[:max_results]
        return ordered

    def _combine_domestic_round_trip(
        self,
        outbound_flights: List[Dict[str, Any]],
        return_flights: List[Dict[str, Any]],
        max_results: int,
    ) -> List[FlightResult]:
        """국내선 왕복 조합을 dedup + top-k(최저가) 방식으로 생성."""
        outbound_flights = [
            f
            for f in outbound_flights
            if f.get("price", 0) > 0 and f.get("depTime") and f.get("arrTime")
        ]
        return_flights = [
            f
            for f in return_flights
            if f.get("price", 0) > 0 and f.get("depTime") and f.get("arrTime")
        ]
        if not outbound_flights or not return_flights:
            return []

        outbound_flights.sort(key=lambda x: x["price"])
        return_flights.sort(key=lambda x: x["price"])
        top_outbound = outbound_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]
        top_return = return_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]

        max_keep = max_results if isinstance(max_results, int) and max_results > 0 else len(top_outbound) * len(top_return)
        max_heap: List[tuple] = []
        seen = set()
        seq = 0

        for ob in top_outbound:
            for ret in top_return:
                total_price = ob["price"] + ret["price"]
                dedup_key = (
                    ob["airline"],
                    ret["airline"],
                    total_price,
                    ob["depTime"],
                    ret["depTime"],
                )
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                seq += 1

                flight = FlightResult(
                    airline=ob["airline"],
                    price=total_price,
                    departure_time=ob["depTime"],
                    arrival_time=ob["arrTime"],
                    stops=ob["stops"],
                    source="Interpark (국내선)",
                    return_departure_time=ret["depTime"],
                    return_arrival_time=ret["arrTime"],
                    return_stops=ret["stops"],
                    is_round_trip=True,
                    outbound_price=ob["price"],
                    return_price=ret["price"],
                    return_airline=ret["airline"],
                )

                entry = (-total_price, -seq, flight)
                if len(max_heap) < max_keep:
                    heapq.heappush(max_heap, entry)
                    continue

                worst_price = -max_heap[0][0]
                worst_seq = -max_heap[0][1]
                if (total_price, seq) < (worst_price, worst_seq):
                    heapq.heapreplace(max_heap, entry)

        ranked = sorted(max_heap, key=lambda x: (-x[0], -x[1]))
        return [entry[2] for entry in ranked]
    
    def search(self, origin: str, destination: str, 
               departure_date: str, return_date: Optional[str] = None,
               adults: int = 1, cabin_class: str = "ECONOMY",
               max_results: int = 1000,
               emit: Callable[[str], None] = None) -> List[FlightResult]:
        """
        항공권 검색 (Playwright 사용, 실패시 수동 모드)
        국내선의 경우 가는편 선택 후 오는편 데이터 추출
        
        Args:
            cabin_class: "ECONOMY" | "BUSINESS" | "FIRST"
        """
        # 성능 측정 시작
        search_start_time = time.time()
        
        def log(msg):
            if emit:
                emit(msg)
            logger.info(msg)
        
        results = []
        url = ""
        profile_dir = ""
        auto_headless = bool(getattr(scraper_config, "AUTO_SEARCH_HEADLESS", True))
        
        # 국내선 여부 확인 (한국 내 공항)
        domestic_airports = {"ICN", "GMP", "CJU", "PUS", "TAE", "SEL"}
        origin_domestic = origin.upper() in domestic_airports or config.CITY_CODES_MAP.get(origin.upper(), origin.upper()) in domestic_airports
        dest_domestic = destination.upper() in domestic_airports or config.CITY_CODES_MAP.get(destination.upper(), destination.upper()) in domestic_airports
        is_domestic = origin_domestic and dest_domestic
        self._last_is_domestic = is_domestic
        
        # 좌석등급 선택 (기본: ECONOMY)
        cabin = cabin_class.upper() if cabin_class else "ECONOMY"
        if cabin not in ["ECONOMY", "BUSINESS", "FIRST"]:
            cabin = "ECONOMY"
        
        try:
            # 컨텍스트 생성 (쿠키/스토리지 저장)
            if getattr(sys, 'frozen', False):
                 app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'FlightBot')
                 profile_dir = os.path.join(app_data, "playwright_profile")
            else:
                 profile_dir = os.path.join(os.getcwd(), "playwright_profile")
            
            os.makedirs(profile_dir, exist_ok=True)

            # 브라우저 초기화 (Persistent Context 포함)
            self._init_browser(
                log_func=log,
                user_data_dir=profile_dir,
                headless=auto_headless,
                block_resources=auto_headless,
            )
            
            if self.context is None:
                self.context = self.browser.new_context(
                    viewport={"width": 1400, "height": 900},
                    locale='ko-KR',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                self._configure_resource_blocking(auto_headless)
            
            self.page = self.context.new_page()
            
            # URL 구성
            # CITY_CODES_MAP에 있으면 도시 코드(c:)로, 없으면 공항 코드(a:)로 처리
            origin_upper = origin.upper()
            dest_upper = destination.upper()
            
            if origin_upper in config.CITY_CODES_MAP:
                origin_code = config.CITY_CODES_MAP[origin_upper]
                origin_prefix = "c"
            else:
                origin_code = origin_upper
                origin_prefix = "a"
            
            if dest_upper in config.CITY_CODES_MAP:
                dest_code = config.CITY_CODES_MAP[dest_upper]
                dest_prefix = "c"
            else:
                dest_code = dest_upper
                dest_prefix = "a"
            
            if return_date:
                url = f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{departure_date}/{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{return_date}?cabin={cabin}&infant=0&child=0&adult={adults}"
            else:
                url = f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{departure_date}?cabin={cabin}&infant=0&child=0&adult={adults}"
            
            if is_domestic:
                log(f"🇰🇷 국내선 검색 모드 ({origin_code} → {dest_code})")
            else:
                log(f"✈️ 국제선 검색 모드")
            if auto_headless:
                log("⚡ 자동 검색 최적화 모드: Headless + 리소스 차단")
            log(f"URL: {url}")
            
            try:
                self.page.goto(url, wait_until='domcontentloaded', timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                log("⚠️ 페이지 로딩 시간 초과 - 계속 진행합니다.")
            except Exception as e:
                raise NetworkError("페이지 로딩 실패", url) from e

            # 결과 로딩 대기
            log("결과 로딩 대기 중...")
            found_data = self._wait_for_results(is_domestic, log)
            if not found_data:
                log("데이터가 충분히 로드되지 않았을 수 있습니다.")
            
            # 국내선 왕복의 경우: 가는편 데이터 먼저 추출 → 클릭 → 오는편 추출 → 병합
            if is_domestic and return_date and found_data:
                log("🇰🇷 국내선 왕복: 가는편/오는편 분리 수집 시작")
                
                try:
                    # Step 1: 가는편 데이터 먼저 추출 (클릭 전)
                    log("📋 1단계: 가는편 목록 추출 중...")
                    outbound_flights = self._extract_domestic_flights_data()
                    log(f"✅ 가는편 {len(outbound_flights)}개 발견")
                    
                    if not outbound_flights:
                        log("⚠️ 가는편 데이터 없음 - 수동 모드 권장")
                        entered_manual = self._enter_manual_mode(
                            url=url,
                            profile_dir=profile_dir,
                            is_domestic=is_domestic,
                            log_func=log,
                            reopen_visible=auto_headless,
                        )
                        if not entered_manual:
                            raise ManualModeActivationError("가는편 데이터 없음 이후 수동 모드 전환에 실패했습니다.")
                        return results
                    
                    # Step 2: 가는편 선택 (오는편 화면으로 전환)
                    log("🔄 2단계: 가는편 선택 → 오는편 화면 전환...")
                    airlines_js = str(self.DOMESTIC_AIRLINES)  # Python 리스트를 JS 배열로 변환
                    best_outbound = min(outbound_flights, key=lambda x: x.get('price', float('inf')))
                    price_text = f"{best_outbound.get('price', 0):,}원" if best_outbound.get('price') else ""
                    js_click = ScraperScripts.get_click_flight_by_details_script(
                        best_outbound.get('airline', ''),
                        best_outbound.get('depTime', ''),
                        best_outbound.get('arrTime', ''),
                        price_text
                    )
                    clicked = self.page.evaluate(js_click)
                    if not clicked:
                        js_click = ScraperScripts.get_click_flight_script(airlines_js)
                        clicked = self.page.evaluate(js_click)
                    
                    if not clicked:
                        log("⚠️ 가는편 선택 실패 - 가는편만 반환")
                        # 가는편만 결과로 반환
                        for ob in outbound_flights:
                            results.append(FlightResult(
                                airline=ob['airline'],
                                price=ob['price'],
                                departure_time=ob['depTime'],
                                arrival_time=ob['arrTime'],
                                stops=ob['stops'],
                                source="Interpark (국내선 가는편)"
                            ))
                        return self._sort_and_limit_results(results, max_results, log)
                    
                    # Step 3: 오는편 로딩 대기
                    log("🕐 3단계: 오는편 로딩 대기...")
                    return_ready = self._wait_for_domestic_return_view()
                    if return_ready:
                        log("✅ 오는편 화면 확인됨")
                    
                    if not return_ready:
                        log("⚠️ 오는편 화면 로딩 실패 - 가는편만 반환")
                        for ob in outbound_flights:
                            results.append(FlightResult(
                                airline=ob['airline'],
                                price=ob['price'],
                                departure_time=ob['depTime'],
                                arrival_time=ob['arrTime'],
                                stops=ob['stops'],
                                source="Interpark (국내선 가는편)"
                            ))
                        return self._sort_and_limit_results(results, max_results, log)
                    
                    # Step 4: 오는편 데이터 추출
                    log("📋 4단계: 오는편 목록 추출 중...")
                    time.sleep(scraper_config.DOMESTIC_RETURN_POST_CLICK_SETTLE_SECONDS)
                    return_flights = self._extract_domestic_flights_data()
                    log(f"✅ 오는편 {len(return_flights)}개 발견")
                    
                    # Step 5: 가는편 + 오는편 결합하여 왕복 결과 생성
                    log("🔗 5단계: 가는편/오는편 결합 중...")
                    
                    if outbound_flights and return_flights:
                        log(
                            f"⚡ 가는편/오는편 조합 계산 중... "
                            f"(상위 {scraper_config.DOMESTIC_COMBINATION_TOP_N}×"
                            f"{scraper_config.DOMESTIC_COMBINATION_TOP_N})"
                        )
                        results = self._combine_domestic_round_trip(
                            outbound_flights,
                            return_flights,
                            max_results=max_results,
                        )
                        log(f"✅ 최저가 기준 상위 {len(results)}개 조합 반환")
                    else:
                        # 가는편만/오는편만 있는 경우
                        for ob in outbound_flights:
                            results.append(FlightResult(
                                airline=ob['airline'],
                                price=ob['price'],
                                departure_time=ob['depTime'],
                                arrival_time=ob['arrTime'],
                                stops=ob['stops'],
                                source="Interpark (국내선 편도)"
                            ))
                    
                    return self._sort_and_limit_results(results, max_results, log)
                    
                except Exception as e:
                    log(f"⚠️ 국내선 처리 중 오류: {e}")
                    logger.error(f"Domestic error: {e}", exc_info=True)

            
            if found_data:
                log("데이터 준비 완료! 추출 시작")
                
                # 페이지 안정화 대기
                time.sleep(scraper_config.SEARCH_PAGE_STABILIZE_SECONDS)
                
                if is_domestic:
                    # 국내선 편도: 버튼 기반 추출
                    log("🇰🇷 국내선 편도 추출")
                    results = self._extract_domestic_prices()

                else:
                    # 국제선: 기존 추출 로직
                    results = self._extract_prices()

                if not results:
                    raise DataExtractionError("자동 추출 결과가 없습니다.")
            else:
                log("데이터가 충분히 로드되지 않았을 수 있습니다.")
                entered_manual = self._enter_manual_mode(
                    url=url,
                    profile_dir=profile_dir,
                    is_domestic=is_domestic,
                    log_func=log,
                    reopen_visible=auto_headless,
                )
                if not entered_manual:
                    raise ManualModeActivationError("결과 로딩 실패 후 수동 모드 전환에 실패했습니다.")

            results = self._sort_and_limit_results(results, max_results, log)
            if results:
                log(f"✅ 자동 추출 성공: {len(results)}개")

                
        except DataExtractionError as e:
            log(f"⚠️ {e} - 수동 모드로 전환")
            entered_manual = self._enter_manual_mode(
                url=url,
                profile_dir=profile_dir,
                is_domestic=is_domestic,
                log_func=log,
                reopen_visible=auto_headless,
            )
            if not entered_manual:
                raise ManualModeActivationError("자동 추출 결과 없음 이후 수동 모드 전환에 실패했습니다.") from e
        except ManualModeActivationError:
            raise
        except Exception as e:
            logger.error(f"Playwright error: {e}", exc_info=True)
            if emit:
                emit(f"오류 발생: {e}")
            entered_manual = self._enter_manual_mode(
                url=url,
                profile_dir=profile_dir,
                is_domestic=is_domestic,
                log_func=log,
                reopen_visible=auto_headless,
            )
            if not entered_manual:
                raise ManualModeActivationError("오류 복구 중 수동 모드 전환에 실패했습니다.") from e
        
        finally:
            # 수동 모드가 아니면 브라우저 정리 (리소스 누수 방지)
            if not self.manual_mode:
                self.close()
            
            # 성능 메트릭 로깅
            elapsed_time = time.time() - search_start_time
            result_count = len(results)
            logger.info(f"📊 검색 완료 - 소요시간: {elapsed_time:.1f}초, 결과: {result_count}건")
            if emit:
                emit(f"📊 검색 완료 ({elapsed_time:.1f}초, {result_count}건)")
        
        return results

    
    def _extract_domestic_flights_data(self) -> list:
        """국내선: 스크롤하며 현재 화면의 항공편 데이터 추출"""
        if not self.page:
            return []
        
        all_flights = {}  # 중복 제거용 dict (key: airline+time+price)
        
        # 스크롤 추적 변수 초기화
        self._no_scroll_count = 0
        self._no_new_count = 0
        self._bottom_count = 0  # 최하단 도달 연속 횟수
        
        # Python 항공사 리스트를 JS 배열 문자열로 변환
        airlines_js = str(self.DOMESTIC_AIRLINES)
        
        try:
            # 스크롤하며 수집 (최대 횟수 도달 또는 스크롤 종료 시 중단)
            for scroll_i in range(scraper_config.DOMESTIC_MAX_SCROLLS):
                js_script = ScraperScripts.get_domestic_list_script(airlines_js)
                
                batch = self.page.evaluate(js_script)
                
                # 중복 제거하며 추가
                new_count = 0
                for f in batch:
                    # 키 생성 방식 변경 (도착시간 포함)
                    key = f.get('key', f'{f["airline"]}_{f["depTime"]}_{f["arrTime"]}_{f["price"]}')
                    if key not in all_flights:
                        all_flights[key] = f
                        new_count += 1
                
                scroll_script = ScraperScripts.get_scroll_check_script()
                scroll_result = self.page.evaluate(scroll_script)
                
                time.sleep(scraper_config.DOMESTIC_SCROLL_PAUSE_SECONDS)
                
                can_scroll = scroll_result.get('canScroll', False)
                reached_bottom = scroll_result.get('reachedBottom', False)
                
                # 최하단 도달 + 새 데이터 없음 로직
                if reached_bottom and new_count == 0:
                    self._bottom_count += 1
                    logger.debug(f"최하단 도달 체크: {self._bottom_count}/3회 (새 항목 없음)")
                    if self._bottom_count >= 3:
                        logger.debug(f"✅ 스크롤 최하단 도달 확인: {len(all_flights)}개 수집 완료, 다음 단계로 진행")
                        break
                    time.sleep(scraper_config.DOMESTIC_SCROLL_BOTTOM_PAUSE_SECONDS)
                    continue
                else:
                    self._bottom_count = 0  # 리셋
                
                # 스크롤이 더 이상 불가능하면 종료
                if not can_scroll:
                    self._no_scroll_count += 1
                    if self._no_scroll_count >= 3:
                        logger.debug(f"스크롤 끝 도달: 더 이상 스크롤할 수 없음 ({len(all_flights)}개 수집)")
                        break
                else:
                    self._no_scroll_count = 0
                
                # 새 항목 없으면 카운트 (lazy loading 대기)
                if new_count == 0:
                    self._no_new_count += 1
                    if self._no_new_count >= 8:  # 8회 연속 새 항목 없으면 종료
                        logger.debug(f"스크롤 조기 종료: {self._no_new_count}회 연속 새 항목 없음 ({len(all_flights)}개 수집)")
                        break
                else:
                    self._no_new_count = 0
            
            result_list = list(all_flights.values())
            logger.info(f"국내선 {len(result_list)}개 항공편 추출 (스크롤 {scroll_i+1}회)")
            return result_list
            
        except Exception as e:
            logger.error(f"Extract domestic data error: {e}", exc_info=True)
            return []

    
    def _extract_domestic_prices(self) -> List[FlightResult]:

        """국내선 전용: button 기반 항공편 정보 추출"""
        if not self.page:
            return []
        
        results = []
        logger.info("🇰🇷 국내선 항공편 추출 시작...")
        
        # Python 항공사 리스트를 JS 배열 문자열로 변환
        airlines_js = str(self.DOMESTIC_AIRLINES)
        
        try:
            js_script = ScraperScripts.get_domestic_prices_script(airlines_js)
            
            extracted = self.page.evaluate(js_script)
            seen = set()
            for item in extracted:
                price = item.get('price', 0)
                dep_time = item.get('depTime', '')
                arr_time = item.get('arrTime', '')
                if price <= 0 or not dep_time or not arr_time:
                    continue
                key = f"{item.get('airline', 'Unknown')}_{dep_time}_{arr_time}_{price}"
                if key in seen:
                    continue
                seen.add(key)
                flight = FlightResult(
                    airline=item.get('airline', 'Unknown'),
                    price=price,
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    stops=item.get('stops', 0),
                    source="Interpark (국내선)",
                    return_departure_time='',
                    return_arrival_time='',
                    return_stops=0,
                    is_round_trip=False
                )
                results.append(flight)
            
            logger.info(f"🇰🇷 국내선 추출 완료: {len(results)}개")
            
        except Exception as e:
            logger.error(f"Domestic extraction error: {e}", exc_info=True)
        
        return results

    
    def _extract_prices(self) -> List[FlightResult]:

        """JavaScript를 이용해 현재 페이지에서 항공권 정보 추출 (스크롤하며 점진적 수집)"""
        if not self.page:
            return []
        
        all_results_dict = {}  # 중복 제거를 위한 딕셔너리 (Key: unique_id)
        max_scrolls = scraper_config.INTERNATIONAL_MAX_SCROLLS
        pause_time = scraper_config.SCROLL_PAUSE_TIME
        
        logger.info(f"📜 점진적 추출 시작 (최대 {max_scrolls}회 스크롤)...")
        
        try:
            previous_height = 0
            
            for i in range(max_scrolls):
                # 1. 현재 화면 데이터 추출
                js_script = ScraperScripts.get_international_prices_script()
                
                step_results = self.page.evaluate(js_script)
                if not step_results and i == 0:
                    fallback_script = ScraperScripts.get_international_prices_fallback_script()
                    fallback_results = self.page.evaluate(fallback_script)
                    if fallback_results:
                        logger.info("국제선 보조 스크립트로 추출 시도")
                        step_results = fallback_results
                
                # 결과 병합
                current_count = 0
                for item in step_results:
                    # 고유 키 생성: 편별 핵심 정보 전체를 포함해 과도한 dedup 방지
                    unique_key = (
                        f"{item.get('airline', '')}|{item.get('price', 0)}|"
                        f"{item.get('depTime', '')}|{item.get('arrTime', '')}|{item.get('stops', 0)}|"
                        f"{item.get('retDepTime', '')}|{item.get('retArrTime', '')}|{item.get('retStops', 0)}"
                    )
                    if unique_key not in all_results_dict:
                        all_results_dict[unique_key] = item
                        current_count += 1
                
                logger.debug(f"✨ 스크롤 {i+1}: 새로운 결과 {current_count}개 추가 (총 {len(all_results_dict)}개)")
                
                # 2. 스크롤 진행
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(pause_time * 1000)
                
                # 3. 높이 변화 체크 (종료 조건)
                new_height = self.page.evaluate("document.body.scrollHeight")
                if new_height == previous_height and i > 2: # 초반에는 변화가 없어도 시도해볼만 함
                     logger.debug("📜 더 이상 새로운 내용이 로딩되지 않습니다.")
                     break
                previous_height = new_height

        except Exception as e:
            logger.error(f"Extraction error: {e}", exc_info=True)
        
        # 딕셔너리를 리스트로 변환
        results = []
        if not all_results_dict:
            fallback_script = ScraperScripts.get_international_prices_fallback_script()
            fallback_results = self.page.evaluate(fallback_script)
            if fallback_results:
                for item in fallback_results:
                    unique_key = (
                        f"{item.get('airline', '')}|{item.get('price', 0)}|"
                        f"{item.get('depTime', '')}|{item.get('arrTime', '')}|{item.get('stops', 0)}|"
                        f"{item.get('retDepTime', '')}|{item.get('retArrTime', '')}|{item.get('retStops', 0)}"
                    )
                    all_results_dict[unique_key] = item
        for item in all_results_dict.values():
             flight = FlightResult(
                airline=item.get('airline', 'Unknown'),
                price=item.get('price', 0),
                departure_time=item.get('depTime', ''),
                arrival_time=item.get('arrTime', ''),
                stops=item.get('stops', 0),
                source="Interpark (Auto)",
                return_departure_time=item.get('retDepTime', ''),
                return_arrival_time=item.get('retArrTime', ''),
                return_stops=item.get('retStops', 0),
                is_round_trip=item.get('isRoundTrip', False)
            )
             results.append(flight)
             
        return results
    
    def extract_from_current_page(self) -> List[FlightResult]:
        """수동 모드: 현재 페이지에서 데이터 추출 (사용자가 호출)"""
        if self._last_is_domestic:
            return self._extract_domestic_prices()
        return self._extract_prices()
    
    def close(self):
        """브라우저 및 리소스 정리"""
        resources = [
            ('page', self.page),
            ('context', self.context),
            ('browser', self.browser),
            ('playwright', self.playwright)
        ]
        
        for name, resource in resources:
            if resource:
                try:
                    if name == 'playwright':
                        resource.stop()
                    else:
                        resource.close()
                except Exception as e:
                    logger.debug(f"{name} 정리 중 오류 (무시됨): {e}")
                finally:
                    setattr(self, name, None)
        
        self.manual_mode = False
    
    def is_manual_mode(self) -> bool:
        """수동 모드 여부 확인"""
        return self.manual_mode and self.page is not None


class FlightSearcher:
    """통합 항공권 검색 엔진"""

    _cache_lock = threading.Lock()
    _search_cache: "OrderedDict[tuple, tuple[float, List[Dict[str, Any]]]]" = OrderedDict()
    
    def __init__(self):
        self.scraper = PlaywrightScraper()
        self.last_results: List[FlightResult] = []

    @staticmethod
    def _build_cache_key(
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int,
        cabin_class: str,
        max_results: int,
    ) -> tuple:
        return (
            (origin or "").upper(),
            (destination or "").upper(),
            departure_date or "",
            return_date or "",
            int(adults or 1),
            (cabin_class or "ECONOMY").upper(),
            int(max_results or 0),
        )

    @classmethod
    def _prune_cache_locked(cls, now: float) -> None:
        ttl = max(1, int(getattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 180)))
        max_entries = max(1, int(getattr(scraper_config, "SEARCH_CACHE_MAX_ENTRIES", 64)))

        expired_keys = []
        for key, (saved_at, _) in cls._search_cache.items():
            if now - saved_at > ttl:
                expired_keys.append(key)
        for key in expired_keys:
            cls._search_cache.pop(key, None)

        while len(cls._search_cache) > max_entries:
            cls._search_cache.popitem(last=False)

    @staticmethod
    def _deserialize_cached_results(payload: List[Dict[str, Any]]) -> List[FlightResult]:
        restored = []
        for row in payload:
            try:
                restored.append(FlightResult(**row))
            except Exception:
                continue
        restored.sort(key=lambda x: x.price if x.price > 0 else float("inf"))
        return restored

    @classmethod
    def _get_cached_results(cls, cache_key: tuple, force_refresh: bool = False) -> Optional[List[FlightResult]]:
        if force_refresh or not getattr(scraper_config, "ENABLE_SEARCH_CACHE", True):
            return None

        now = time.time()
        with cls._cache_lock:
            cls._prune_cache_locked(now)
            item = cls._search_cache.get(cache_key)
            if not item:
                return None
            saved_at, payload = item
            ttl = max(1, int(getattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 180)))
            if now - saved_at > ttl:
                cls._search_cache.pop(cache_key, None)
                return None
            cls._search_cache.move_to_end(cache_key)
        return cls._deserialize_cached_results(payload)

    @classmethod
    def _store_cached_results(cls, cache_key: tuple, results: List[FlightResult]) -> None:
        if not results or not getattr(scraper_config, "ENABLE_SEARCH_CACHE", True):
            return

        payload = []
        for item in results:
            try:
                payload.append(item.to_dict())
            except Exception:
                continue
        if not payload:
            return

        now = time.time()
        with cls._cache_lock:
            cls._prune_cache_locked(now)
            cls._search_cache[cache_key] = (now, payload)
            cls._search_cache.move_to_end(cache_key)
            cls._prune_cache_locked(now)

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            cls._search_cache.clear()
    
    def search(self, origin: str, destination: str, 
               departure_date: str, return_date: Optional[str] = None,
               adults: int = 1, cabin_class: str = "ECONOMY",
               max_results: int = 1000,
               progress_callback: Callable = None,
               force_refresh: bool = False) -> List[FlightResult]:
        """항공권 검색 진입점"""
        def emit(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        cabin_label = {"ECONOMY": "이코노미", "BUSINESS": "비즈니스", "FIRST": "일등석"}.get(cabin_class.upper(), "이코노미")
        emit(f"🔍 {origin} → {destination} 항공권 검색 시작 ({cabin_label})")

        cache_key = self._build_cache_key(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            cabin_class=cabin_class,
            max_results=max_results,
        )
        cached_results = self._get_cached_results(cache_key, force_refresh=force_refresh)
        if cached_results is not None:
            self.last_results = cached_results
            cheapest = cached_results[0] if cached_results else None
            if cheapest:
                emit(f"⚡ 캐시 사용: {len(cached_results)}개 결과, 최저가 {cheapest.price:,}원")
            else:
                emit("⚡ 캐시 사용: 결과 없음")
            return cached_results
        
        results = self.scraper.search(
            origin, destination, 
            departure_date, return_date, 
            adults, cabin_class,
            max_results, 
            emit
        )
        self.last_results = results
        
        if results:
            if not self.scraper.is_manual_mode():
                self._store_cached_results(cache_key, results)
            cheapest = results[0]
            emit(f"✅ 검색 완료: {len(results)}개 발견, 최저가 {cheapest.price:,}원")
        elif self.scraper.is_manual_mode():
            emit("🖐️ 수동 모드 활성화 - 브라우저에서 결과 로딩 후 '추출' 버튼을 누르세요")
        else:
            emit("❌ 검색 결과 없음")
        
        return results
    
    def extract_manual(self) -> List[FlightResult]:
        """수동 모드에서 데이터 추출 재시도"""
        results = self.scraper.extract_from_current_page()
        results.sort(key=lambda x: x.price if x.price > 0 else float('inf'))
        self.last_results = results
        return results
    
    def is_manual_mode(self) -> bool:
        return self.scraper.is_manual_mode()
    
    def close(self):
        self.scraper.close()
    
    def get_cheapest(self) -> Optional[FlightResult]:
        if self.last_results:
            return self.last_results[0]
        return None


class ParallelSearcher:
    """다중 검색을 병렬로 실행하는 검색 엔진"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = min(max_concurrent, 4)  # 최대 4개로 제한
        self.results = {}
        self._lock = None
    
    def search_multiple_destinations(self, origin: str, destinations: List[str],
                                     departure_date: str, return_date: Optional[str] = None,
                                     adults: int = 1, cabin_class: str = "ECONOMY",
                                     progress_callback: Callable = None) -> Dict[str, List[FlightResult]]:
        """여러 목적지를 병렬로 검색"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self._lock = threading.Lock()
        self.results = {}
        
        def search_single(dest: str) -> tuple:
            """단일 목적지 검색"""
            searcher = FlightSearcher()
            try:
                def emit(msg):
                    if progress_callback:
                        progress_callback(f"[{dest}] {msg}")
                    logger.info(f"[{dest}] {msg}")
                
                results = searcher.scraper.search(
                    origin, dest, departure_date, return_date, 
                    adults, cabin_class, max_results=500, emit=emit
                )
                return dest, results
            except Exception as e:
                logger.error(f"Parallel search error for {dest}: {e}")
                return dest, []
            finally:
                searcher.close()
        
        if progress_callback:
            progress_callback(f"🚀 병렬 검색 시작: {len(destinations)}개 목적지 (동시 {self.max_concurrent}개)")
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {executor.submit(search_single, dest): dest for dest in destinations}
            
            for future in as_completed(futures):
                try:
                    dest, results = future.result()
                    with self._lock:
                        self.results[dest] = results
                        
                    if progress_callback:
                        count = len(results)
                        cheapest = min((r.price for r in results), default=0) if results else 0
                        progress_callback(f"✅ {dest} 완료: {count}개 결과, 최저가 {cheapest:,}원")
                except Exception as e:
                    logger.error(f"Future error: {e}")
        
        if progress_callback:
            progress_callback(f"🏁 병렬 검색 완료: {len(self.results)}개 목적지")
        
        return self.results
    
    def search_date_range(self, origin: str, destination: str,
                          dates: List[str], return_offset: int = 0,
                          adults: int = 1, cabin_class: str = "ECONOMY",
                          progress_callback: Callable = None) -> Dict[str, tuple]:
        """여러 날짜를 병렬로 검색"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime, timedelta
        
        self._lock = threading.Lock()
        date_results = {}
        
        def search_single_date(dep_date: str) -> tuple:
            """단일 날짜 검색"""
            ret_date = None
            if return_offset > 0:
                try:
                    dt = datetime.strptime(dep_date, "%Y%m%d")
                    ret_date = (dt + timedelta(days=return_offset)).strftime("%Y%m%d")
                except Exception:
                    pass
            
            searcher = FlightSearcher()
            try:
                # 조용히 실행
                results = searcher.scraper.search(
                    origin, destination, dep_date, ret_date,
                    adults, cabin_class, max_results=100, emit=lambda msg: None
                )
                
                if results:
                    cheapest = min(results, key=lambda x: x.price)
                    return dep_date, (cheapest.price, cheapest.airline)
                return dep_date, (0, "N/A")
            except Exception as e:
                logger.error(f"Date search error for {dep_date}: {e}")
                return dep_date, (0, "Error")
            finally:
                searcher.close()
        
        if progress_callback:
            progress_callback(f"🚀 날짜 병렬 검색: {len(dates)}일 (동시 {self.max_concurrent}개)")
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {executor.submit(search_single_date, d): d for d in dates}
            completed = 0
            
            for future in as_completed(futures):
                try:
                    dep_date, price_info = future.result()
                    with self._lock:
                        date_results[dep_date] = price_info
                        completed += 1
                    
                    if progress_callback:
                        price, airline = price_info
                        if price > 0:
                            progress_callback(f"📅 {dep_date}: {price:,}원 ({airline}) [{completed}/{len(dates)}]")
                        else:
                            progress_callback(f"📅 {dep_date}: 결과 없음 [{completed}/{len(dates)}]")
                except Exception as e:
                    logger.error(f"Future error: {e}")
        
        if progress_callback:
            progress_callback(f"🏁 날짜 검색 완료: {len(date_results)}일")
        
        return date_results


if __name__ == "__main__":
    searcher = FlightSearcher()
    try:
        print("\n=== Playwright 테스트 (서울 → 도쿄) ===")
        # 테스트를 위해 30일 후 날짜 생성
        from datetime import datetime, timedelta
        d1 = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        d2 = (datetime.now() + timedelta(days=35)).strftime("%Y%m%d")
        
        results = searcher.search("ICN", "NRT", d1, d2)
        
        if results:
            print(f"\n{len(results)}개 결과:")
            for i, r in enumerate(results[:5], 1):
                stops = "직항" if r.stops == 0 else f"{r.stops}회 경유"
                print(f"{i}. {r.airline} - {r.price:,}원 | {r.departure_time} -> {r.arrival_time}")
        else:
            print("결과 없음 또는 수동 모드 전환됨")
    finally:
        searcher.close()
