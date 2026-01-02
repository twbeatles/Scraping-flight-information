"""
Flight Scraper V2 - Playwright + Manual Mode
Uses Playwright for scraping with manual fallback when auto-extraction fails.
"""

import time
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
import logging
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

import config

# 로거 설정 (중복 핸들러 방지)
logger = logging.getLogger("ScraperV2")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)



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

    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "airline": self.airline,
            "price": self.price,
            "currency": self.currency,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "duration": self.duration,
            "stops": self.stops,
            "flight_number": self.flight_number,
            "source": self.source,
            "return_departure_time": self.return_departure_time,
            "return_arrival_time": self.return_arrival_time,
            "return_stops": self.return_stops,
            "is_round_trip": self.is_round_trip
        }


class PlaywrightScraper:
    """Playwright 기반 스크래퍼 - 수동 모드 지원"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.manual_mode = False
    
    def search(self, origin: str, destination: str, 
               departure_date: str, return_date: Optional[str] = None,
               adults: int = 1, emit: Callable[[str], None] = None) -> List[FlightResult]:
        """
        항공권 검색 (Playwright 사용, 실패시 수동 모드)
        국내선의 경우 가는편 선택 후 오는편 데이터 추출
        """
        def log(msg):
            if emit:
                emit(msg)
            logger.info(msg)
        
        results = []
        
        # 국내선 여부 확인 (한국 내 공항)
        domestic_airports = {"ICN", "GMP", "CJU", "PUS", "TAE", "SEL"}
        origin_domestic = origin.upper() in domestic_airports or config.CITY_CODES_MAP.get(origin.upper(), origin.upper()) in domestic_airports
        dest_domestic = destination.upper() in domestic_airports or config.CITY_CODES_MAP.get(destination.upper(), destination.upper()) in domestic_airports
        is_domestic = origin_domestic and dest_domestic
        
        try:
            log("Playwright 브라우저 시작 중...")
            
            self.playwright = sync_playwright().start()
            
            # 브라우저 시작 (visible 모드 - 수동 모드 대비)
            self.browser = self.playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )
            
            # 컨텍스트 생성 (쿠키/스토리지 저장)
            profile_dir = os.path.join(os.getcwd(), "playwright_profile")
            os.makedirs(profile_dir, exist_ok=True)
            
            context = self.browser.new_context(
                viewport={"width": 1400, "height": 900},
                locale='ko-KR',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            self.page = context.new_page()
            
            # URL 구성
            origin_city = config.CITY_CODES_MAP.get(origin.upper(), origin.upper())
            dest_city = config.CITY_CODES_MAP.get(destination.upper(), destination.upper())
            
            if return_date:
                url = f"https://travel.interpark.com/air/search/c:{origin_city}-c:{dest_city}-{departure_date}/c:{dest_city}-c:{origin_city}-{return_date}?cabin=ECONOMY&infant=0&child=0&adult={adults}"
            else:
                url = f"https://travel.interpark.com/air/search/c:{origin_city}-c:{dest_city}-{departure_date}?cabin=ECONOMY&infant=0&child=0&adult={adults}"
            
            if is_domestic:
                log(f"🇰🇷 국내선 검색 모드 ({origin_city} → {dest_city})")
            else:
                log(f"✈️ 국제선 검색 모드")
            log(f"URL: {url}")
            
            try:
                self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            except PlaywrightTimeoutError:
                log("⚠️ 페이지 로딩 시간 초과 - 계속 진행합니다.")

            # 결과 로딩 대기
            log("결과 로딩 대기 중...")
            
            # 30초 동안 가격 정보가 나타날 때까지 대기
            found_data = False
            for i in range(10):
                # 가격 요소 확인 (휴리스틱)
                count = self.page.locator("text=원").count()
                
                if count >= 10:
                    found_data = True
                    break
                
                log(f"데이터 대기 중... ({i*3}/30초)")
                time.sleep(3)
            
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
                        self.manual_mode = True
                        return results
                    
                    # Step 2: 첫 번째 가는편 선택 (오는편 화면으로 전환)
                    log("🔄 2단계: 가는편 선택 → 오는편 화면 전환...")
                    js_click = """
                    () => {
                        const airlines = ['대한항공', '아시아나', '제주항공', '진에어', '티웨이', 
                                          '에어부산', '에어서울', '이스타항공', '하이에어'];
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = btn.textContent || '';
                            if (/\\d{2}:\\d{2}\\s*-\\s*\\d{2}:\\d{2}/.test(text) && 
                                /[0-9,]+\\s*원/.test(text) &&
                                airlines.some(a => text.includes(a))) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    """
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
                        return results
                    
                    # Step 3: 오는편 로딩 대기
                    log("🕐 3단계: 오는편 로딩 대기...")
                    time.sleep(4)
                    
                    # 오는편 화면 확인
                    for j in range(5):
                        page_text = self.page.content()
                        if "오는편" in page_text:
                            log("✅ 오는편 화면 확인됨")
                            break
                        time.sleep(2)
                    
                    # Step 4: 오는편 데이터 추출
                    log("📋 4단계: 오는편 목록 추출 중...")
                    time.sleep(2)
                    return_flights = self._extract_domestic_flights_data()
                    log(f"✅ 오는편 {len(return_flights)}개 발견")
                    
                    # Step 5: 가는편 + 오는편 결합하여 왕복 결과 생성
                    log("🔗 5단계: 가는편/오는편 결합 중...")
                    
                    # 다양한 오는편 옵션 제공 (가격순 상위 5개)
                    if outbound_flights and return_flights:
                        # 오는편을 가격순으로 정렬하여 상위 5개 선택
                        sorted_returns = sorted(return_flights, key=lambda x: x['price'])
                        top_returns = sorted_returns[:5]  # 최저가 5개 오는편
                        
                        # 각 가는편에 대해 상위 오는편 조합 생성
                        for ob in outbound_flights:
                            for ret in top_returns:
                                flight = FlightResult(
                                    airline=ob['airline'],
                                    price=ob['price'] + ret['price'],  # 왕복 합산
                                    departure_time=ob['depTime'],
                                    arrival_time=ob['arrTime'],
                                    stops=ob['stops'],
                                    source="Interpark (국내선)",
                                    return_departure_time=ret['depTime'],
                                    return_arrival_time=ret['arrTime'],
                                    return_stops=ret['stops'],
                                    is_round_trip=True,
                                    outbound_price=ob['price'],  # 가는편 가격
                                    return_price=ret['price']  # 오는편 가격
                                )
                                results.append(flight)
                        
                        # 중복 제거 (같은 가격, 같은 시간대 제거)
                        seen = set()
                        unique_results = []
                        for r in results:
                            key = (r.airline, r.price, r.departure_time, r.return_departure_time)
                            if key not in seen:
                                seen.add(key)
                                unique_results.append(r)
                        results = unique_results
                        
                        log(f"✅ 왕복 {len(results)}개 조합 생성 완료 (가는편 {len(outbound_flights)} x 오는편 {len(top_returns)})")
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
                    
                    return results
                    
                except Exception as e:
                    log(f"⚠️ 국내선 처리 중 오류: {e}")
                    logger.error(f"Domestic error: {e}", exc_info=True)

            
            if found_data:
                log("데이터 준비 완료! 추출 시작")
                
                # 페이지 안정화 대기 (스레드 오류 방지)
                time.sleep(2)
                
                if is_domestic:
                    # 국내선 편도: 버튼 기반 추출
                    log("🇰🇷 국내선 편도 추출")
                    results = self._extract_domestic_prices()

                else:
                    # 국제선: 기존 추출 로직
                    results = self._extract_prices()
            else:
                log("데이터가 충분히 로드되지 않았을 수 있습니다.")

            if results:
                log(f"✅ 자동 추출 성공: {len(results)}개")
            else:
                log("⚠️ 자동 추출 실패 또는 결과 없음 - 수동 모드로 전환")
                self.manual_mode = True

                
        except Exception as e:
            logger.error(f"Playwright error: {e}", exc_info=True)
            if emit:
                emit(f"오류 발생: {e}")
            self.manual_mode = True
        
        return results

    
    def _extract_domestic_flights_data(self) -> list:
        """국내선: 스크롤하며 현재 화면의 항공편 데이터 추출
        Returns: list of dicts with airline, price, depTime, arrTime, stops
        """
        if not self.page:
            return []
        
        all_flights = {}  # 중복 제거용 dict (key: airline+time+price)
        
        try:
            # 스크롤하며 수집 (최대 300회 - 스크롤 끝 도달 시 자동 중단)
            for scroll_i in range(300):
                js_script = r"""
                () => {
                    const results = [];
                    const airlines = ['대한항공', '아시아나', '제주항공', '진에어', '티웨이', 
                                      '에어부산', '에어서울', '이스타항공', '하이에어'];
                    
                    const buttons = document.querySelectorAll('button');
                    
                    for (const btn of buttons) {
                        try {
                            const text = btn.textContent || '';
                            
                            // 시간 패턴 확인 (16:50 - 18:05)
                            const timeMatch = text.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/);
                            if (!timeMatch) continue;
                            
                            // 가격 확인 - 더 엄격하게 (앞에 공백이나 줄바꿈이 있는 숫자,숫자 원)
                            // 10,000원 ~ 999,999원 범위만
                            const priceMatches = text.match(/(\d{2,3},\d{3})\s*원/g);
                            if (!priceMatches || priceMatches.length === 0) continue;
                            
                            // 첫 번째 가격만 사용 (가장 저렴한 가격이 먼저 표시됨)
                            const firstPrice = priceMatches[0].replace(/[^\d]/g, '');
                            const price = parseInt(firstPrice);
                            
                            // 가격 범위 검증 (국내선: 2만원 ~ 50만원)
                            if (price < 20000 || price > 500000) continue;
                            
                            // 광고 제외
                            if (text.includes('이벤트') || text.includes('프로모션')) continue;
                            
                            // 항공사 찾기
                            let airline = '기타';
                            for (const a of airlines) {
                                if (text.includes(a)) {
                                    airline = a;
                                    break;
                                }
                            }
                            
                            // 경유 확인
                            let stops = 0;
                            if (text.includes('경유')) {
                                stops = 1;
                            }
                            
                            results.push({
                                airline: airline,
                                price: price,
                                depTime: timeMatch[1],
                                arrTime: timeMatch[2],
                                stops: stops,
                                key: airline + '_' + timeMatch[1] + '_' + timeMatch[2] + '_' + price  // 중복 체크 강화 (도착시간 추가)
                            });
                        } catch (e) { }
                    }
                    
                    return results;
                }
                """
                
                batch = self.page.evaluate(js_script)
                
                # 중복 제거하며 추가
                new_count = 0
                for f in batch:
                    # 키 생성 방식 변경 (도착시간 포함)
                    key = f.get('key', f'{f["airline"]}_{f["depTime"]}_{f["arrTime"]}_{f["price"]}')
                    if key not in all_flights:
                        all_flights[key] = f
                        new_count += 1
                    # else:
                        # logger.debug(f"중복 항목 무시: {key}")
                
                # 스크롤 다운 및 스크롤 가능 여부 확인
                can_scroll = self.page.evaluate("""
                    () => {
                        const beforeScroll = window.scrollY;
                        const beforeHeight = document.body.scrollHeight;
                        
                        // 1. 우선 window 스크롤 시도 (가장 일반적)
                        const totalHeight = document.body.scrollHeight;
                        const currentScroll = window.scrollY + window.innerHeight;
                        
                        if (currentScroll < totalHeight) {
                            window.scrollBy(0, 500);  // 500px씩 더 세밀하게 스크롤
                        } else {
                            // 2. 만약 window 스크롤이 끝이라면 특정 컨테이너 스크롤 시도
                             const containers = [
                                document.querySelector('div[scrollable="true"]'),
                                document.querySelector('[class*="flightList"]'),
                                document.querySelector('[class*="resultList"]'),
                                document.querySelector('.ReactVirtualizados'),
                                document.querySelector('div[style*="overflow"]'),
                            ];
                            
                            for (const container of containers) {
                                if (container && container.scrollHeight > container.clientHeight) {
                                    container.scrollTop += 500;  // 500px씩 더 세밀하게
                                }
                            }
                        }
                        
                        // 스크롤 후 위치 변화 확인
                        const afterScroll = window.scrollY;
                        const afterHeight = document.body.scrollHeight;
                        
                        // 스크롤 위치나 페이지 높이가 변했으면 아직 스크롤 가능
                        return (afterScroll !== beforeScroll) || (afterHeight !== beforeHeight);
                    }
                """)
                time.sleep(1.0)  # 데이터 로딩 시간
                
                # 스크롤이 더 이상 불가능하면 종료
                if not can_scroll:
                    no_scroll_count = getattr(self, '_no_scroll_count', 0) + 1
                    self._no_scroll_count = no_scroll_count
                    if no_scroll_count >= 3:  # 3회 연속 스크롤 불가 시 종료
                        logger.info(f"스크롤 끝 도달: 더 이상 스크롤할 수 없음")
                        break
                else:
                    self._no_scroll_count = 0
                
                # 새 항목 없으면 카운트 (lazy loading 대기)
                if new_count == 0:
                    no_new_count = getattr(self, '_no_new_count', 0) + 1
                    self._no_new_count = no_new_count
                    if no_new_count >= 10:  # 10회 연속 새 항목 없으면 종료
                        logger.info(f"스크롤 조기 종료: {no_new_count}회 연속 새 항목 없음")
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
        
        try:
            js_script = r"""
            () => {
                const results = [];
                const airlines = ['대한항공', '아시아나', '제주항공', '진에어', '티웨이', 
                                  '에어부산', '에어서울', '이스타항공', '하이에어'];
                
                const allButtons = document.querySelectorAll('button');
                
                for (const btn of allButtons) {
                    try {
                        const text = btn.textContent || '';
                        
                        // 시간 패턴 확인 (16:50 - 18:05)
                        const timeMatch = text.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/);
                        if (!timeMatch) continue;
                        
                        // 가격 확인 (28,900 원)
                        const priceMatch = text.match(/([0-9,]+)\s*원/);
                        if (!priceMatch) continue;
                        
                        // 항공사 찾기
                        let airline = '기타';
                        for (const a of airlines) {
                            if (text.includes(a)) {
                                airline = a;
                                break;
                            }
                        }
                        
                        // 경유 확인
                        let stops = 0;
                        if (text.includes('경유')) {
                            const stopMatch = text.match(/(\d)회\s*경유/);
                            if (stopMatch) stops = parseInt(stopMatch[1]);
                            else stops = 1;
                        }
                        
                        const price = parseInt(priceMatch[1].replace(/,/g, ''));
                        
                        results.push({
                            airline: airline,
                            price: price,
                            depTime: timeMatch[1],
                            arrTime: timeMatch[2],
                            stops: stops,
                            retDepTime: '',
                            retArrTime: '',
                            retStops: 0,
                            isRoundTrip: false
                        });
                    } catch (e) { }
                }
                
                return results;
            }
            """
            
            extracted = self.page.evaluate(js_script)
            
            for item in extracted:
                flight = FlightResult(
                    airline=item.get('airline', 'Unknown'),
                    price=item.get('price', 0),
                    departure_time=item.get('depTime', ''),
                    arrival_time=item.get('arrTime', ''),
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
        max_scrolls = 20
        pause_time = 1.0 # 초
        
        logger.info(f"📜 점진적 추출 시작 (최대 {max_scrolls}회 스크롤)...")
        
        try:
            previous_height = 0
            
            for i in range(max_scrolls):
                # 1. 현재 화면 데이터 추출
                js_script = r"""
                () => {
                    const results = [];
                    const cards = document.querySelectorAll('li[data-index]');
                    
                    for (const card of cards) {
                        try {
                            const allSpans = Array.from(card.querySelectorAll('span'));
                            const priceEl = allSpans.find(el => /^[0-9,]+\s*원$/.test(el.textContent.trim()));
                            if (!priceEl) continue;
                            
                            const price = parseInt(priceEl.textContent.replace(/[^0-9]/g, ''));
                            
                            const timeSpans = allSpans.filter(el => /^\d{2}:\d{2}$/.test(el.textContent.trim()));
                            const times = timeSpans.map(el => el.textContent.trim());
                            
                            if (times.length < 2) continue;
                            
                            const logoImgs = card.querySelectorAll('img[alt$="로고"]');
                            let airline = "기타";
                            if (logoImgs.length > 0) {
                                airline = logoImgs[0].alt.replace(' 로고', '');
                            }
                            
                            const cardText = card.textContent;
                            let stops = 0;
                            let retStops = 0;
                            
                            const stopMatches = cardText.match(/(\d)회\s*경유/g);
                            
                            if (stopMatches) {
                                stops = parseInt(stopMatches[0].replace(/[^0-9]/g, ''));
                                retStops = (stopMatches.length > 1) ? parseInt(stopMatches[1].replace(/[^0-9]/g, '')) : stops;
                            } else if (cardText.includes("직항")) {
                                stops = 0; retStops = 0;
                            } else {
                                 stops = 1; retStops = 1;
                            }

                            const isRoundTrip = times.length >= 4;

                            results.push({
                                airline: airline,
                                price: price,
                                depTime: times[0],
                                arrTime: times[1],
                                stops: stops,
                                retDepTime: isRoundTrip ? times[2] : '',
                                retArrTime: isRoundTrip ? times[3] : '',
                                retStops: isRoundTrip ? retStops : 0,
                                isRoundTrip: isRoundTrip
                            });
                        } catch (e) { }
                    }
                    return results;
                }
                """
                
                step_results = self.page.evaluate(js_script)
                
                # 결과 병합
                current_count = 0
                for item in step_results:
                    # 고유 키 생성: 가격-출발시간-항공사
                    unique_key = f"{item['price']}-{item['depTime']}-{item['airline']}"
                    if unique_key not in all_results_dict:
                        all_results_dict[unique_key] = item
                        current_count += 1
                
                logger.info(f"✨ 스크롤 {i+1}: 새로운 결과 {current_count}개 추가 (총 {len(all_results_dict)}개)")
                
                # 2. 스크롤 진행
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(pause_time * 1000)
                
                # 3. 높이 변화 체크 (종료 조건)
                new_height = self.page.evaluate("document.body.scrollHeight")
                if new_height == previous_height and i > 2: # 초반에는 변화가 없어도 시도해볼만 함
                     logger.info("📜 더 이상 새로운 내용이 로딩되지 않습니다.")
                     break
                previous_height = new_height

        except Exception as e:
            logger.error(f"Extraction error: {e}", exc_info=True)
        
        # 딕셔너리를 리스트로 변환
        results = []
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
        return self._extract_prices()
    
    def close(self):
        """브라우저 종료"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass
        finally:
            self.browser = None
            self.page = None
            self.playwright = None
            self.manual_mode = False
    
    def is_manual_mode(self) -> bool:
        """수동 모드 여부 확인"""
        return self.manual_mode and self.page is not None


class FlightSearcher:
    """통합 항공권 검색 엔진"""
    
    def __init__(self):
        self.scraper = PlaywrightScraper()
        self.last_results: List[FlightResult] = []
    
    def search(self, origin: str, destination: str, 
               departure_date: str, return_date: Optional[str] = None,
               adults: int = 1, progress_callback: Callable = None) -> List[FlightResult]:
        """항공권 검색 진입점"""
        def emit(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        emit(f"🔍 {origin} → {destination} 항공권 검색 시작")
        
        results = self.scraper.search(
            origin, destination, 
            departure_date, return_date, 
            adults, emit
        )
        
        # 가격순 정렬
        results.sort(key=lambda x: x.price if x.price > 0 else float('inf'))
        self.last_results = results
        
        if results:
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
