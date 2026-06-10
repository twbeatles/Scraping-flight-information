"""International DOM fallback extraction path."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

import scraping.interpark as scraper_config
from scraping.interpark.scripts import ScraperScripts
from scraping.models import FlightResult
from scraping.international.helpers import _browser_item_unique_key
from scraping.international.normalizer import _build_international_results

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def _extract_international_prices_from_dom(scraper: "PlaywrightScraper") -> List[FlightResult]:
    if not scraper.page:
        return []

    all_results_dict: Dict[str, Dict[str, Any]] = {}
    max_scrolls = scraper_config.INTERNATIONAL_MAX_SCROLLS
    pause_time = scraper_config.SCROLL_PAUSE_TIME
    logger.info("📜 점진적 추출 시작 (최대 %s회 스크롤)...", max_scrolls)
    seen_indices: set[int] = set()
    stalled_iterations = 0

    try:
        for index in range(max_scrolls):
            step_results = scraper.page.evaluate(ScraperScripts.get_international_prices_script())
            step_source = "international_primary"
            step_confidence = 0.9

            if not step_results and index == 0:
                fallback_results = scraper.page.evaluate(
                    ScraperScripts.get_international_prices_fallback_script()
                )
                if fallback_results:
                    logger.info("국제선 보조 스크립트로 재시도")
                    step_results = fallback_results
                    step_source = "international_fallback"
                    step_confidence = 0.6

            current_count = 0
            for item in step_results or []:
                item.setdefault("extraction_source", step_source)
                item.setdefault("confidence", step_confidence)
                unique_key = _browser_item_unique_key(item)
                if unique_key in all_results_dict:
                    continue
                all_results_dict[unique_key] = item
                current_count += 1

            current_indices = _read_current_result_indices(scraper)
            before_index_count = len(seen_indices)
            seen_indices.update(current_indices)
            new_index_count = len(seen_indices) - before_index_count

            logger.info(
                "🧭 스크롤 %s: 새 결과 %s개 추가 (총 %s개, index %s개)",
                index + 1,
                current_count,
                len(all_results_dict),
                len(seen_indices),
            )

            scroll_state = _advance_results_scroll(scraper)
            scraper.page.wait_for_timeout(pause_time * 1000)

            if current_count == 0 and new_index_count == 0:
                stalled_iterations += 1
            else:
                stalled_iterations = 0

            if (not scroll_state.get("advanced", False) and stalled_iterations >= 2) or stalled_iterations >= 4:
                logger.info("🧭 더 이상 새 콘텐츠가 로드되지 않습니다.")
                break
    except Exception as exc:
        logger.error("Extraction error: %s", exc, exc_info=True)

    if not all_results_dict and scraper.page:
        fallback_results = scraper.page.evaluate(ScraperScripts.get_international_prices_fallback_script())
        for item in fallback_results or []:
            item.setdefault("extraction_source", "international_fallback")
            item.setdefault("confidence", 0.6)
            all_results_dict[_browser_item_unique_key(item)] = item

    sorted_indices = sorted(seen_indices)
    dom_gap_detected = any(
        sorted_indices[idx] - sorted_indices[idx - 1] > 1
        for idx in range(1, len(sorted_indices))
    )
    scraper._search_metrics.update(
        {
            "dom_seen_indices": sorted_indices,
            "dom_gap_detected": dom_gap_detected,
        }
    )
    if dom_gap_detected:
        scraper._manual_reason = "dom_fallback_gap_risk"

    return _build_international_results(all_results_dict.values())


def _read_current_result_indices(scraper: "PlaywrightScraper") -> List[int]:
    if not scraper.page:
        return []

    script = """
    () => Array.from(document.querySelectorAll('li[data-index], div[data-index]'))
        .map((node) => Number(node.getAttribute('data-index')))
        .filter((value) => Number.isFinite(value))
    """
    result = scraper.page.evaluate(script)
    if not isinstance(result, list):
        return []
    return sorted({int(item) for item in result if isinstance(item, (int, float))})


def _advance_results_scroll(scraper: "PlaywrightScraper") -> Dict[str, Any]:
    if not scraper.page:
        return {"advanced": False, "atEnd": True}

    script = """
    () => {
        const cards = Array.from(document.querySelectorAll('li[data-index], div[data-index]'));
        const candidates = Array.from(document.querySelectorAll('*'))
            .filter((el) => {
                const style = getComputedStyle(el);
                const overflowY = style.overflowY;
                return (
                    (overflowY === 'auto' || overflowY === 'scroll') &&
                    el.scrollHeight > el.clientHeight + 20 &&
                    cards.some((card) => el.contains(card))
                );
            })
            .sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));

        const target = candidates[0];
        if (target) {
            const maxTop = Math.max(0, target.scrollHeight - target.clientHeight);
            const beforeTop = target.scrollTop;
            const nextTop = Math.min(maxTop, beforeTop + Math.max(Math.floor(target.clientHeight * 0.8), 320));
            target.scrollTop = nextTop;
            target.dispatchEvent(new Event('scroll', { bubbles: true }));
            return {
                advanced: nextTop !== beforeTop,
                atEnd: nextTop >= maxTop,
                scrollTop: nextTop,
                maxTop,
                mode: 'container',
            };
        }

        const beforeY = window.scrollY;
        const maxY = Math.max(0, document.body.scrollHeight - window.innerHeight);
        const nextY = Math.min(maxY, beforeY + Math.max(Math.floor(window.innerHeight * 0.8), 320));
        window.scrollTo(0, nextY);
        return {
            advanced: nextY !== beforeY,
            atEnd: nextY >= maxY,
            scrollTop: nextY,
            maxTop: maxY,
            mode: 'window',
        };
    }
    """
    result = scraper.page.evaluate(script)
    return result if isinstance(result, dict) else {"advanced": False, "atEnd": True}
