"""Domestic-result JavaScript builders for Interpark pages."""

from scraping.interpark.selectors import REGEX_STOPS, REGEX_TIME


def get_domestic_list_script(airlines_js_list):
    """Build JS that extracts domestic flight list rows."""
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

            const readBenefit = (text, airline, basePrice) => {{
                const matches = Array.from(text.matchAll(boundaryPricePattern));
                if (matches.length < 2) {{
                    return {{ benefitPrice: 0, benefitLabel: '' }};
                }}

                const finalMatch = matches[matches.length - 1];
                const benefitPrice = parseInt(finalMatch[1].replace(/,/g, ''), 10);
                if (!benefitPrice || benefitPrice === basePrice) {{
                    return {{ benefitPrice: 0, benefitLabel: '' }};
                }}

                const firstMatch = matches[0];
                const firstEnd = (firstMatch.index || 0) + firstMatch[0].length;
                const finalStart = finalMatch.index || 0;
                let benefitLabel = normalize(text.slice(firstEnd, finalStart));
                if (airline && benefitLabel.startsWith(airline)) {{
                    benefitLabel = normalize(benefitLabel.slice(airline.length));
                }}
                benefitLabel = benefitLabel.replace(/^[\\s:|·,/-]+/, '').replace(/[\\s:|·,/-]+$/, '');
                return {{
                    benefitPrice,
                    benefitLabel,
                }};
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
                    const benefit = readBenefit(text, airline, price);

                    results.push({{
                        airline: airline,
                        price: price,
                        benefitPrice: benefit.benefitPrice,
                        benefitLabel: benefit.benefitLabel,
                        depTime: timeMatch[1],
                        arrTime: timeMatch[2],
                        stops: readStops(text),
                        key: `${{airline}}_${{timeMatch[1]}}_${{timeMatch[2]}}_${{price}}_${{benefit.benefitPrice}}`
                    }});
                }} catch (e) {{ }}
            }}
            return results;
        }}
        """


def get_domestic_prices_script(airlines_js_list):
    """Build JS that extracts domestic prices from button-based rows."""
    return get_domestic_list_script(airlines_js_list)
