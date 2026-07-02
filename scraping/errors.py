"""Scraper domain exceptions."""

class ScraperError(Exception):
    """스크래퍼 기본 예외"""
    pass

class BrowserInitError(ScraperError):
    """브라우저 초기화 실패"""
    def __init__(self, message: str = "브라우저를 시작할 수 없습니다."):
        self.message = message
        super().__init__(self.message)

class ManualModeActivationError(ScraperError):
    """Automatic extraction failed and manual mode could not be opened."""
    def __init__(self, message: str = "수동 모드로 전환하지 못했습니다."):
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


class SearchCancelledError(ScraperError):
    """사용자 또는 worker가 검색 취소를 요청한 경우."""

    def __init__(self, message: str = "검색이 취소되었습니다."):
        self.message = message
        super().__init__(self.message)
