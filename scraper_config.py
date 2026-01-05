
"""
Configuration and Scripts for Flight Scraper V2
"""

# === 타임아웃 및 재시도 설정 ===
MAX_RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 2
PAGE_LOAD_TIMEOUT_MS = 60000
DATA_WAIT_TIMEOUT_SECONDS = 30
SCROLL_PAUSE_TIME = 1.0

# === 정규표현식 패턴 (Python & JS 공용) ===
# JS에서 사용할 때는 이스케이프 처리가 필요할 수 있음
REGEX_TIME = r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})"
REGEX_PRICE = r"(\d{1,3},\d{3},?\d{0,3})\s*원"
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
            
            const buttons = document.querySelectorAll('button');
            
            for (const btn of buttons) {{
                try {{
                    const text = btn.textContent || '';
                    
                    // 시간 패턴
                    const timeMatch = text.match(/{REGEX_TIME}/);
                    if (!timeMatch) continue;
                    
                    // 가격 패턴
                    const priceMatch = text.match(/{REGEX_PRICE}/);
                    if (!priceMatch) continue;
                    
                    const firstPrice = priceMatch[1].replace(/[^\\d]/g, '');
                    const price = parseInt(firstPrice);
                    
                    if (price < 1000 || price > 10000000) continue;
                    if (text.includes('이벤트') || text.includes('프로모션')) continue;
                    
                    let airline = '기타';
                    for (const a of airlines) {{
                        if (text.includes(a)) {{
                            airline = a;
                            break;
                        }}
                    }}
                    
                    let stops = 0;
                    if (text.includes('경유')) {{
                        stops = 1;
                    }}
                    
                    results.push({{
                        airline: airline,
                        price: price,
                        depTime: timeMatch[1],
                        arrTime: timeMatch[2],
                        stops: stops
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """

    @staticmethod
    def get_domestic_prices_script(airlines_js_list):
        """국내선 가격 추출 JS (버튼 기반)"""
        return f"""
        () => {{
            const results = [];
            const airlines = {airlines_js_list};
            const allButtons = document.querySelectorAll('button');
            
            for (const btn of allButtons) {{
                try {{
                    const text = btn.textContent || '';
                    
                    const timeMatch = text.match(/{REGEX_TIME}/);
                    if (!timeMatch) continue;
                    
                    const priceMatch = text.match(/{REGEX_PRICE}/);
                    if (!priceMatch) continue;
                    
                    let airline = '기타';
                    for (const a of airlines) {{
                        if (text.includes(a)) {{
                            airline = a;
                            break;
                        }}
                    }}
                    
                    let stops = 0;
                    if (text.includes('경유')) {{
                        const stopMatch = text.match(/{REGEX_STOPS}/);
                        if (stopMatch) stops = parseInt(stopMatch[1]);
                        else stops = 1;
                    }}
                    
                    const price = parseInt(priceMatch[1].replace(/,/g, ''));
                    
                    results.push({{
                        airline: airline,
                        price: price,
                        depTime: timeMatch[1],
                        arrTime: timeMatch[2],
                        stops: stops
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """

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
