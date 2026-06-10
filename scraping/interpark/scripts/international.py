"""International-result JavaScript builders for Interpark pages."""

from scraping.interpark.selectors import REGEX_STOPS, REGEX_TIME


def get_international_prices_script():
    """Build JS that extracts international prices from indexed cards."""
    return f"""
        () => {{
            const results = [];
            const cards = document.querySelectorAll('li[data-index], div[data-index]');
            const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const exactPricePattern = /^(\\d{{1,3}}(?:,\\d{{3}}){{1,2}})\\s*원$/;
            const boundaryPricePattern = /(?:^|[^0-9,])(\\d{{1,3}}(?:,\\d{{3}}){{1,2}})\\s*원/g;

            const readPrice = (card) => {{
                const nodes = [card, ...card.querySelectorAll('p, span, div, strong, em')];
                for (const node of nodes) {{
                    const text = normalize(node.textContent);
                    if (!text) continue;
                    const exactMatch = text.match(exactPricePattern);
                    if (exactMatch) {{
                        return parseInt(exactMatch[1].replace(/,/g, ''), 10);
                    }}
                }}

                const fallbackMatches = Array.from(
                    normalize(card.textContent).matchAll(boundaryPricePattern)
                );
                if (fallbackMatches.length > 0) {{
                    return parseInt(fallbackMatches[0][1].replace(/,/g, ''), 10);
                }}
                return 0;
            }};

            const readTimes = (card) => {{
                const ordered = [];
                const pushTime = (value) => {{
                    if (!value) return;
                    if (ordered.length === 0 || ordered[ordered.length - 1] !== value) {{
                        ordered.push(value);
                    }}
                }};

                const nodes = [card, ...card.querySelectorAll('p, span, div, strong, em')];
                for (const node of nodes) {{
                    const text = normalize(node.textContent);
                    if (!text) continue;
                    const rangeMatch = text.match(/^(\\d{{2}}:\\d{{2}})\\s*-\\s*(\\d{{2}}:\\d{{2}})$/);
                    if (rangeMatch) {{
                        pushTime(rangeMatch[1]);
                        pushTime(rangeMatch[2]);
                        continue;
                    }}
                    if (/^\\d{{2}}:\\d{{2}}$/.test(text)) {{
                        pushTime(text);
                    }}
                }}

                if (ordered.length >= 2) {{
                    return ordered;
                }}

                const cardText = normalize(card.textContent);
                const rangeMatches = cardText.match(/{REGEX_TIME}/g) || [];
                for (const raw of rangeMatches) {{
                    const parts = raw.match(/{REGEX_TIME}/);
                    if (parts && parts.length >= 3) {{
                        pushTime(parts[1]);
                        pushTime(parts[2]);
                    }}
                }}
                return ordered;
            }};

            const readAirlines = (card) => {{
                const logoNames = Array.from(card.querySelectorAll('img[alt$="로고"]'))
                    .map((img) => normalize((img.getAttribute('alt') || '').replace(/\\s*로고$/, '')))
                    .filter(Boolean);

                const unique = [];
                for (const name of logoNames) {{
                    if (!unique.includes(name)) {{
                        unique.push(name);
                    }}
                }}
                return unique;
            }};

            const readStops = (text, isRoundTrip) => {{
                const stopMatches = Array.from(text.matchAll(/{REGEX_STOPS}/g))
                    .map((match) => parseInt(match[1], 10) || 0);
                const directCount = (text.match(/직항/g) || []).length;

                let outbound = 0;
                let inbound = 0;

                if (stopMatches.length > 0) {{
                    outbound = stopMatches[0];
                }} else if (text.includes('경유')) {{
                    outbound = 1;
                }}

                if (isRoundTrip) {{
                    if (stopMatches.length > 1) {{
                        inbound = stopMatches[1];
                    }} else if (directCount >= 2) {{
                        inbound = 0;
                    }} else if (directCount === 0 && text.includes('경유')) {{
                        inbound = outbound || 1;
                    }}
                }}

                return {{ outbound, inbound }};
            }};

            for (const card of cards) {{
                try {{
                    const price = readPrice(card);
                    if (price < 1000) continue;

                    const times = readTimes(card);
                    if (times.length < 2) continue;
                    const isRoundTrip = times.length >= 4;
                    const airlines = readAirlines(card);
                    const airline = airlines[0] || "기타";
                    const returnAirline = isRoundTrip ? (airlines[1] || airline) : '';
                    const stops = readStops(normalize(card.textContent), isRoundTrip);

                    results.push({{
                        airline: airline,
                        returnAirline: returnAirline,
                        price: price,
                        depTime: times[0],
                        arrTime: times[1],
                        stops: stops.outbound,
                        retDepTime: isRoundTrip ? times[2] : '',
                        retArrTime: isRoundTrip ? times[3] : '',
                        retStops: isRoundTrip ? stops.inbound : 0,
                        isRoundTrip: isRoundTrip
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """


def get_international_prices_fallback_script():
    """Build fallback JS for international price extraction."""
    return f"""
        () => {{
            const results = [];
            const candidates = document.querySelectorAll(
                'li[data-index], div[data-index], li[class*="result"], div[class*="result"], li[class*="ticket"], div[class*="ticket"]'
            );
            const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const boundaryPricePattern = /(?:^|[^0-9,])(\\d{{1,3}}(?:,\\d{{3}}){{1,2}})\\s*원/g;

            const readAirlines = (card) => {{
                const logoNames = Array.from(card.querySelectorAll('img[alt$="로고"]'))
                    .map((img) => normalize((img.getAttribute('alt') || '').replace(/\\s*로고$/, '')))
                    .filter(Boolean);
                const unique = [];
                for (const name of logoNames) {{
                    if (!unique.includes(name)) {{
                        unique.push(name);
                    }}
                }}
                return unique;
            }};

            for (const card of candidates) {{
                try {{
                    const text = normalize(card.textContent);
                    const priceMatches = Array.from(text.matchAll(boundaryPricePattern));
                    if (priceMatches.length === 0) continue;
                    const price = parseInt(priceMatches[0][1].replace(/,/g, ''), 10);

                    const timeMatches = text.match(/{REGEX_TIME}/g) || [];
                    const times = [];
                    for (const t of timeMatches) {{
                        const parts = t.match(/{REGEX_TIME}/);
                        if (parts && parts.length >= 3) {{
                            times.push(parts[1], parts[2]);
                        }}
                    }}
                    if (times.length < 2) continue;

                    const isRoundTrip = times.length >= 4;
                    const airlines = readAirlines(card);
                    const airline = airlines[0] || "기타";
                    const returnAirline = isRoundTrip ? (airlines[1] || airline) : '';

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

                    results.push({{
                        airline: airline,
                        returnAirline: returnAirline,
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
