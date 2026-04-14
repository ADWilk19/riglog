class FitbitError(Exception):
    pass


class FitbitAuthError(FitbitError):
    pass


class FitbitAPIError(FitbitError):
    pass


class FitbitRateLimitError(FitbitAPIError):
    pass


class FitbitNetworkError(FitbitError):
    pass
