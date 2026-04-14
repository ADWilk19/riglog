# app/services/activity/fitbit_client.py

from __future__ import annotations

from typing import Any

import requests

from app.services.activity.fitbit_auth import get_fitbit_session
from app.services.activity.fitbit_exceptions import (
    FitbitAPIError,
    FitbitAuthError,
    FitbitNetworkError,
    FitbitRateLimitError,
)


class FitbitClient:
    BASE_URL = "https://api.fitbit.com/1/user/-"

    def __init__(self) -> None:
        self.session = get_fitbit_session()

    def get_daily_steps(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        url = (
            f"{self.BASE_URL}/activities/steps/date/"
            f"{start_date}/{end_date}.json"
        )

        response = self._get_with_retry(url)
        payload: dict[str, Any] = response.json()

        return payload.get("activities-steps", [])

    def _get_with_retry(self, url: str):
        response = self._safe_request(url)

        if response.status_code == 401:
            # retry once after rebuilding session
            self.session = get_fitbit_session()
            response = self._safe_request(url)

        self._handle_errors(response)
        return response

    def _safe_request(self, url: str):
        try:
            return self.session.get(url, timeout=20)
        except requests.exceptions.RequestException as exc:
            raise FitbitNetworkError(f"Network error contacting Fitbit: {exc}") from exc

    def _handle_errors(self, response):
        if response.status_code < 400:
            return

        if response.status_code == 401:
            raise FitbitAuthError("Fitbit authentication failed. Reconnect required.")

        if response.status_code == 429:
            raise FitbitRateLimitError("Fitbit rate limit exceeded.")

        try:
            body = response.json()
        except Exception:
            body = response.text

        raise FitbitAPIError(f"Fitbit API error {response.status_code}: {body}")
