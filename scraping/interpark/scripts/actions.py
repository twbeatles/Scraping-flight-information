"""Click/action JavaScript builders for Interpark pages."""

import json

from scraping.interpark.selectors import REGEX_TIME


def get_click_flight_script(airlines_js_list):
    """Build JS that clicks a flight matching any configured airline."""
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


def get_click_flight_by_details_script(
    airline: str,
    dep_time: str,
    arr_time: str,
    price_text: str,
    flight_number: str = "",
):
    """Build JS that clicks a flight matching airline/time/price details."""
    airline_js = json.dumps(airline or "")
    dep_js = json.dumps(dep_time or "")
    arr_js = json.dumps(arr_time or "")
    price_js = json.dumps(price_text or "")
    flight_js = json.dumps(flight_number or "")
    return f"""
        () => {{
            const airline = {airline_js};
            const dep = {dep_js};
            const arr = {arr_js};
            const priceText = {price_js};
            const flightNumber = {flight_js};
            const buttons = Array.from(document.querySelectorAll('button'));
            const scored = [];
            for (const btn of buttons) {{
                const text = (btn.textContent || '').replace(/\\s+/g, ' ').trim();
                if (!text) continue;
                let score = 0;
                if (airline && text.includes(airline)) score += 3;
                if (dep && text.includes(dep)) score += 2;
                if (arr && text.includes(arr)) score += 2;
                if (priceText && text.includes(priceText)) score += 2;
                if (flightNumber && text.includes(flightNumber)) score += 4;
                if (score < 5) continue;
                scored.push({{ btn, score }});
            }}
            scored.sort((a, b) => b.score - a.score);
            if (scored.length > 0) {{
                scored[0].btn.click();
                return true;
            }}
            // Fallback: exact previous matching rules without flight number.
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
