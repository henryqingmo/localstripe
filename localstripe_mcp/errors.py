class StripeAPIError(Exception):
    """Raised when localstripe returns a non-2xx response or is unreachable."""

    def __init__(self, status: int, message: str, code: str | None = None):
        super().__init__(f"[{status} {code or 'error'}] {message}")
        self.status = status
        self.message = message
        self.code = code
