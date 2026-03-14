
"""
Configuration and Scripts for Flight Scraper V2
"""

import json
from datetime import datetime

import config

# === 타임아웃 및 재시도 설정 ===
MAX_RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 2
PAGE_LOAD_TIMEOUT_MS = 60000
DATA_WAIT_TIMEOUT_SECONDS = 30
SCROLL_PAUSE_TIME = 1.0

# === 성능/대기 튜닝 상수 ===
FILTER_DEBOUNCE_MS = 120
SEARCH_PAGE_STABILIZE_SECONDS = 1.5
DOMESTIC_RETURN_WAIT_TIMEOUT_SECONDS = 15
DOMESTIC_RETURN_POST_CLICK_SETTLE_SECONDS = 0.5
DOMESTIC_SCROLL_PAUSE_SECONDS = 0.3
DOMESTIC_SCROLL_BOTTOM_PAUSE_SECONDS = 0.5
DOMESTIC_MAX_SCROLLS = 300
DOMESTIC_COMBINATION_TOP_N = 150
INTERNATIONAL_MAX_SCROLLS = 20
SELECTOR_HEALTH_WINDOW = 200
INTERPARK_SEARCH_URL_BASE = "https://travel.interpark.com/air/search"


def normalize_interpark_date(date_text: str | None) -> str:
    """Convert supported user-facing date formats to Interpark's compact path format."""
    if not date_text:
        return ""

    value = str(date_text).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y%m%d")
        except ValueError:
            continue

    raise ValueError(f"Unsupported Interpark date format: {date_text}")


def resolve_interpark_location(code: str) -> tuple[str, str]:
    """Return the route prefix and normalized city/airport code for Interpark URLs."""
    normalized = (code or "").strip().upper()
    if normalized in config.CITY_CODES_MAP:
        return "c", config.CITY_CODES_MAP[normalized]
    return "a", normalized


def build_interpark_search_url(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    *,
    cabin: str = "ECONOMY",
    adults: int = 1,
    infant: int = 0,
    child: int = 0,
) -> str:
    """Build a canonical Interpark search URL with compact dates."""
    origin_prefix, origin_code = resolve_interpark_location(origin)
    dest_prefix, dest_code = resolve_interpark_location(destination)
    departure = normalize_interpark_date(departure_date)
    returning = normalize_interpark_date(return_date) if return_date else ""

    route = f"{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{departure}"
    if returning:
        route = (
            f"{route}/"
            f"{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{returning}"
        )

    safe_cabin = (cabin or "ECONOMY").upper()
    safe_adults = max(1, int(adults or 1))

    return (
        f"{INTERPARK_SEARCH_URL_BASE}/{route}"
        f"?cabin={safe_cabin}&infant={int(infant)}&child={int(child)}&adult={safe_adults}"
    )

# === 결과 대기 selector 후보 (DOM 변경 대응) ===
DOMESTIC_WAIT_SELECTORS = [
    "button:has-text(\"원\")",
    "text=/\\d{1,3}(,\\d{3})+\\s*원/",
    "button:has-text(\"직항\")",
]
INTERNATIONAL_WAIT_SELECTORS = [
    "li[data-index]",
    "div[data-index]",
    "li[class*=\"result\"]",
    "text=/\\d{1,3}(,\\d{3})+\\s*원/",
]

# === 정규표현식 패턴 (Python & JS 공용) ===
# JS에서 사용할 때는 이스케이프 처리가 필요할 수 있음
REGEX_TIME = r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})"
REGEX_PRICE = r"(?:^|[^\d,])(\d{1,3}(?:,\d{3}){1,2})\s*원"
REGEX_STOPS = r"(\d)회\s*경유"

# === JavaScript 스크립트 템플릿 ===

class ScraperScripts:
    
    @staticmethod
    def get_click_flight_script(airlines_js_list):
        """특정 항공사의 항공편을 클릭하는 JS 스크립트"""
        return f"""
        () => {{
            const airlines = {airlines_js_list};
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {{
                const text = btn.textContent || '';
                // 시간 및 가격 패턴 확인
                if (/{REGEX_TIME}/.test(text) && 
                    /[0-9,]+\\s*원/.test(text) &&
                    airlines.some(a => text.includes(a))) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}
        """

    @staticmethod
    def get_domestic_list_script(airlines_js_list):
        """국내선 목록 예비 추출 JS"""
        return f"""
        () => {{
            const results = [];
            const airlines = {airlines_js_list};

            const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const exactPricePattern = /^(\\d{{1,3}}(?:,\\d{{3}}){{1,2}})\\s*원$/;
            const boundaryPricePattern = /(?:^|[^0-9,])(\\d{{1,3}}(?:,\\d{{3}}){{1,2}})\\s*원/g;

            const readPrice = (button) => {{
                const nodes = [button, ...button.querySelectorAll('p, span, strong, em, div')];
                for (const node of nodes) {{
                    const text = normalize(node.textContent);
                    if (!text) continue;
                    const exactMatch = text.match(exactPricePattern);
                    if (exactMatch) {{
                        return parseInt(exactMatch[1].replace(/,/g, ''), 10);
                    }}
                }}

                const fallbackMatches = Array.from(
                    normalize(button.textContent).matchAll(boundaryPricePattern)
                );
                if (fallbackMatches.length > 0) {{
                    return parseInt(fallbackMatches[0][1].replace(/,/g, ''), 10);
                }}
                return 0;
            }};

            const readAirline = (button, text) => {{
                const texts = Array.from(button.querySelectorAll('p, span, div'))
                    .map((node) => normalize(node.textContent))
                    .filter(Boolean);

                for (const airlineName of airlines) {{
                    if (texts.some((entry) => entry === airlineName || entry.includes(airlineName))) {{
                        return airlineName;
                    }}
                }}

                for (const airlineName of airlines) {{
                    if (text.includes(airlineName)) {{
                        return airlineName;
                    }}
                }}

                return '';
            }};

            const readStops = (text) => {{
                if (text.includes('직항')) {{
                    return 0;
                }}

                const stopMatch = text.match(/{REGEX_STOPS}/);
                if (stopMatch) {{
                    return parseInt(stopMatch[1], 10) || 0;
                }}
                return text.includes('경유') ? 1 : 0;
            }};

            for (const btn of document.querySelectorAll('button')) {{
                try {{
                    const text = normalize(btn.textContent);
                    const timeMatch = text.match(/{REGEX_TIME}/);
                    if (!timeMatch) continue;

                    const airline = readAirline(btn, text);
                    if (!airline) continue;

                    const price = readPrice(btn);
                    if (price < 1000 || price > 10000000) continue;
                    if (text.includes('이벤트') || text.includes('프로모션')) continue;

                    results.push({{
                        airline: airline,
                        price: price,
                        depTime: timeMatch[1],
                        arrTime: timeMatch[2],
                        stops: readStops(text),
                        key: `${{airline}}_${{timeMatch[1]}}_${{timeMatch[2]}}_${{price}}`
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """

    @staticmethod
    def get_domestic_prices_script(airlines_js_list):
        """국내선 가격 추출 JS (버튼 기반)"""
        return ScraperScripts.get_domestic_list_script(airlines_js_list)

    @staticmethod
    def get_international_prices_script():
        """국제선 가격 추출 JS (li[data-index] 기반)"""
        return f"""
        () => {{
            const results = [];
            const cards = document.querySelectorAll('li[data-index]');
            
            for (const card of cards) {{
                try {{
                    const allSpans = Array.from(card.querySelectorAll('span'));
                    const priceEl = allSpans.find(el => /^[0-9,]+\\s*원$/.test(el.textContent.trim()));
                    if (!priceEl) continue;
                    
                    const price = parseInt(priceEl.textContent.replace(/[^0-9]/g, ''));
                    
                    // 시간 추출 (HH:MM 형식)
                    const timeSpans = allSpans.filter(el => /^\\d{{2}}:\\d{{2}}$/.test(el.textContent.trim()));
                    const times = timeSpans.map(el => el.textContent.trim());
                    
                    if (times.length < 2) continue;
                    
                    // 항공사 로고 alt 텍스트
                    const logoImgs = card.querySelectorAll('img[alt$="로고"]');
                    let airline = "기타";
                    if (logoImgs.length > 0) {{
                        airline = logoImgs[0].alt.replace(' 로고', '');
                    }}
                    
                    const cardText = card.textContent;
                    let stops = 0;
                    let retStops = 0;
                    
                    const stopMatches = cardText.match(/{REGEX_STOPS}/g);
                    
                    if (stopMatches) {{
                        stops = parseInt(stopMatches[0].replace(/[^0-9]/g, ''));
                        retStops = (stopMatches.length > 1) ? parseInt(stopMatches[1].replace(/[^0-9]/g, '')) : stops;
                    }} else if (cardText.includes("직항")) {{
                        stops = 0; retStops = 0;
                    }} else {{
                        stops = 1; retStops = 1;
                    }}

                    // 왕복 여부 판단 (시간이 4개 이상이면 왕복)
                    const isRoundTrip = times.length >= 4;

                    results.push({{
                        airline: airline,
                        price: price,
                        depTime: times[0],
                        arrTime: times[1],
                        stops: stops,
                        retDepTime: isRoundTrip ? times[2] : '',
                        retArrTime: isRoundTrip ? times[3] : '',
                        retStops: isRoundTrip ? retStops : 0,
                        isRoundTrip: isRoundTrip
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """

    @staticmethod
    def get_click_flight_by_details_script(airline: str, dep_time: str, arr_time: str, price_text: str):
        """특정 항공편(항공사/시간/가격) 클릭 JS"""
        airline_js = json.dumps(airline or "")
        dep_js = json.dumps(dep_time or "")
        arr_js = json.dumps(arr_time or "")
        price_js = json.dumps(price_text or "")
        return f"""
        () => {{
            const airline = {airline_js};
            const dep = {dep_js};
            const arr = {arr_js};
            const priceText = {price_js};
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {{
                const text = btn.textContent || '';
                if (airline && !text.includes(airline)) continue;
                if (dep && !text.includes(dep)) continue;
                if (arr && !text.includes(arr)) continue;
                if (priceText && !text.includes(priceText)) continue;
                btn.click();
                return true;
            }}
            return false;
        }}
        """

    @staticmethod
    def get_international_prices_fallback_script():
        """국제선 가격 추출 보조 JS (구조 변경 대비)"""
        return f"""
        () => {{
            const results = [];
            const candidates = document.querySelectorAll(
                'li[data-index], div[data-index], li[class*="result"], div[class*="result"], li[class*="ticket"], div[class*="ticket"]'
            );

            for (const card of candidates) {{
                try {{
                    const text = card.textContent || '';
                    const priceMatch = text.match(/{REGEX_PRICE}/);
                    if (!priceMatch) continue;
                    const price = parseInt(priceMatch[1].replace(/[^0-9]/g, ''));

                    const timeMatches = text.match(/{REGEX_TIME}/g) || [];
                    const times = [];
                    for (const t of timeMatches) {{
                        const parts = t.match(/{REGEX_TIME}/);
                        if (parts && parts.length >= 3) {{
                            times.push(parts[1], parts[2]);
                        }}
                    }}
                    if (times.length < 2) continue;

                    let airline = "기타";
                    const logoImgs = card.querySelectorAll('img[alt]');
                    if (logoImgs.length > 0) {{
                        airline = logoImgs[0].alt.replace(' 로고', '').trim();
                    }}

                    let stops = 0;
                    let retStops = 0;
                    const stopMatches = text.match(/{REGEX_STOPS}/g);
                    if (stopMatches) {{
                        stops = parseInt(stopMatches[0].replace(/[^0-9]/g, ''));
                        retStops = (stopMatches.length > 1)
                            ? parseInt(stopMatches[1].replace(/[^0-9]/g, ''))
                            : stops;
                    }} else if (text.includes("직항")) {{
                        stops = 0;
                        retStops = 0;
                    }} else {{
                        stops = 1;
                        retStops = 1;
                    }}

                    const isRoundTrip = times.length >= 4;
                    results.push({{
                        airline: airline,
                        price: price,
                        depTime: times[0],
                        arrTime: times[1],
                        stops: stops,
                        retDepTime: isRoundTrip ? times[2] : '',
                        retArrTime: isRoundTrip ? times[3] : '',
                        retStops: retStops,
                        isRoundTrip: isRoundTrip
                    }});
                    if (results.length >= 300) break;
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """

    @staticmethod
    def get_scroll_check_script():
        """스크롤 가능 여부 및 최하단 도달 체크 JS"""
        return """
        () => {
            const beforeScroll = window.scrollY;
            const beforeHeight = document.body.scrollHeight;
            
            // 1. 우선 window 스크롤 시도
            const totalHeight = document.body.scrollHeight;
            const currentScroll = window.scrollY + window.innerHeight;
            
            // 최하단 여부 먼저 체크
            const isAtBottom = (totalHeight - currentScroll) <= 5;
            
            if (!isAtBottom) {
                window.scrollBy(0, 500); 
            } else {
                // 2. 컨테이너 스크롤 시도
                const containers = [
                    document.querySelector('div[scrollable="true"]'),
                    document.querySelector('[class*="flightList"]'),
                    document.querySelector('[class*="resultList"]'),
                    document.querySelector('.ReactVirtualizados'),
                    document.querySelector('div[style*="overflow"]'),
                ];
                
                for (const container of containers) {
                    if (container && container.scrollHeight > container.clientHeight) {
                        const containerAtBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) <= 5;
                        if (!containerAtBottom) {
                            container.scrollTop += 500;
                            break;
                        }
                    }
                }
            }
            
            const afterScroll = window.scrollY;
            const afterHeight = document.body.scrollHeight;
            
            const canScroll = (afterScroll !== beforeScroll) || (afterHeight !== beforeHeight);
            
            const finalTotalHeight = document.body.scrollHeight;
            const finalCurrentScroll = window.scrollY + window.innerHeight;
            const reachedBottom = (finalTotalHeight - finalCurrentScroll) <= 5;
            
            return {
                canScroll: canScroll,
                reachedBottom: reachedBottom && !canScroll
            };
        }
        """
