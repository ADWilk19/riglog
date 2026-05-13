# app/services/activity/fitbit_client.py
from __future__ import annotations

import os
from typing import Any

import requests

from app.services.activity.fitbit_auth import get_fitbit_session, TOKEN_URL
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

    def get_intraday_activity(
    self,
    resource: str,
    activity_date: str,
    detail_level: str = "15min",
) -> list[dict[str, Any]]:
        """
        Fetch Fitbit intraday activity data for a single resource and date.

        Args:
            resource: Fitbit activity resource, e.g. "steps" or "calories".
            activity_date: Date string in YYYY-MM-DD format.
            detail_level: Fitbit detail level, e.g. "1min" or "15min".

        Returns:
            Fitbit intraday dataset rows, usually containing time and value.
        """
        url = (
            f"{self.BASE_URL}/activities/{resource}/date/"
            f"{activity_date}/1d/{detail_level}.json"
        )

        response = self._get_with_retry(url)
        payload: dict[str, Any] = response.json()

        intraday_key = f"activities-{resource}-intraday"

        return payload.get(intraday_key, {}).get("dataset", [])

    def _get_with_retry(self, url: str):
        response = self._safe_request(url)

        if response.status_code == 401:
            try:
                # force refresh using OAuth2Session
                self.session.refresh_token(
                    TOKEN_URL,
                    client_id=self.session.client_id,
                    client_secret=os.environ["FITBIT_CLIENT_SECRET"],
                )
            except Exception:
                raise FitbitAuthError("Fitbit authentication failed. Reconnect required.")

            # retry after refresh
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
