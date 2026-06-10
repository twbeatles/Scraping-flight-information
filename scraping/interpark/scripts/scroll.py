"""Scroll JavaScript builders for Interpark pages."""


def get_scroll_check_script():
    """Build JS that scrolls the current result container and reports progress."""
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
