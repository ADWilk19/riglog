"""Translate Google Health responses to RigLog's existing Fitbit row format."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from app.services.activity.fitbit_auth import get_fitbit_session
from app.services.activity.fitbit_exceptions import (
    FitbitAPIError, FitbitAuthError, FitbitNetworkError, FitbitRateLimitError,
)


def _civil(day: date) -> dict:
    return {"date": {"year": day.year, "month": day.month, "day": day.day}, "time": {}}


class FitbitClient:
    BASE_URL = "https://health.googleapis.com/v4/users/me"
    SOURCE_FAMILY = "users/me/dataSourceFamilies/google-sources"

    def __init__(self) -> None:
        self.session = get_fitbit_session()
        self._timezone = None

    def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self.session.request(method, url, timeout=20, **kwargs)
        except requests.exceptions.RequestException:
            raise FitbitNetworkError("Network error contacting Google Health.") from None
        if response.status_code == 401:
            raise FitbitAuthError("Google Health authentication failed. Reconnect required.")
        if response.status_code == 403:
            raise FitbitAuthError("Check Google Health API access and reconnect with all requested permissions.")
        if response.status_code == 429:
            raise FitbitRateLimitError("Google Health rate limit exceeded.")
        if response.status_code >= 400:
            raise FitbitAPIError(f"Google Health API error (HTTP {response.status_code}).")
        try:
            return response.json()
        except ValueError:
            raise FitbitAPIError("Google Health returned an invalid response.") from None

    def _rollup(self, data_type: str, method: str, body: dict):
        body = {**body, "dataSourceFamily": self.SOURCE_FAMILY}
        while True:
            payload = self._request(
                "POST", f"{self.BASE_URL}/dataTypes/{data_type}/dataPoints:{method}", json=body,
            )
            yield from payload.get("rollupDataPoints", [])
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
            body = {**body, "pageToken": page_token}

    def get_daily_steps(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        rows = []
        while start <= end:
            stop = min(start + timedelta(days=90), end + timedelta(days=1))
            for point in self._rollup("steps", "dailyRollUp", {
                "range": {"start": _civil(start), "end": _civil(stop)}, "windowSizeDays": 1,
            }):
                day = point["civilStartTime"]["date"]
                rows.append({"dateTime": date(**day).isoformat(),
                             "value": int(point.get("steps", {}).get("countSum", 0))})
            start = stop
        return sorted(rows, key=lambda row: row["dateTime"])

    def get_intraday_activity(self, resource: str, activity_date: str,
                              detail_level: str = "15min") -> list[dict[str, Any]]:
        if resource not in {"steps", "calories"} or detail_level not in {"1min", "15min"}:
            raise ValueError("Expected steps/calories and 1min/15min detail.")
        if self._timezone is None:
            settings = self._request("GET", f"{self.BASE_URL}/settings")
            try:
                self._timezone = ZoneInfo(settings["timeZone"])
            except (KeyError, ValueError, ZoneInfoNotFoundError):
                raise FitbitAPIError("Set a valid timezone in Google Health before syncing intraday data.") from None
        day = date.fromisoformat(activity_date)
        start = datetime.combine(day, time(), self._timezone)
        end = datetime.combine(day + timedelta(days=1), time(), self._timezone)
        data_type, field, value = (("steps", "steps", "countSum") if resource == "steps"
                                   else ("total-calories", "totalCalories", "kcalSum"))
        # RigLog stores local wall-clock timestamps; combine repeated DST buckets.
        buckets = {}
        for point in self._rollup(data_type, "rollUp", {
            "range": {"startTime": start.astimezone(timezone.utc).isoformat(),
                      "endTime": end.astimezone(timezone.utc).isoformat()},
            "windowSize": "60s" if detail_level == "1min" else "900s",
        }):
            if field not in point:
                continue
            local = datetime.fromisoformat(point["startTime"].replace("Z", "+00:00")).astimezone(self._timezone)
            clock = local.strftime("%H:%M:%S")
            amount = int(point[field][value]) if resource == "steps" else float(point[field][value])
            buckets[clock] = buckets.get(clock, 0) + amount
        return [{"time": clock, "value": amount} for clock, amount in sorted(buckets.items())]
