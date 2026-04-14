from app.services.activity.fitbit_exceptions import (
    FitbitAuthError,
    FitbitNetworkError,
    FitbitRateLimitError,
)
from app.services.activity.fitbit_client import FitbitClient


def test_get_daily_steps_success(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "activities-steps": [
            {"dateTime": "2026-04-01", "value": "12345"},
        ]
    }

    mock_session = mocker.Mock()
    mock_session.get.return_value = mock_response

    mocker.patch(
        "app.services.activity.fitbit_client.get_fitbit_session",
        return_value=mock_session,
    )

    client = FitbitClient()
    rows = client.get_daily_steps("2026-04-01", "2026-04-01")

    assert rows == [{"dateTime": "2026-04-01", "value": "12345"}]


def test_retries_once_on_401_then_succeeds(mocker):
    first_response = mocker.Mock()
    first_response.status_code = 401

    second_response = mocker.Mock()
    second_response.status_code = 200
    second_response.json.return_value = {
        "activities-steps": [
            {"dateTime": "2026-04-01", "value": "9000"},
        ]
    }

    first_session = mocker.Mock()
    first_session.get.return_value = first_response

    second_session = mocker.Mock()
    second_session.get.return_value = second_response

    mocker.patch(
        "app.services.activity.fitbit_client.get_fitbit_session",
        side_effect=[first_session, second_session],
    )

    client = FitbitClient()
    rows = client.get_daily_steps("2026-04-01", "2026-04-01")

    assert rows == [{"dateTime": "2026-04-01", "value": "9000"}]


def test_raises_fitbit_auth_error_after_second_401(mocker):
    first_response = mocker.Mock()
    first_response.status_code = 401

    second_response = mocker.Mock()
    second_response.status_code = 401
    second_response.text = "Unauthorized"

    first_session = mocker.Mock()
    first_session.get.return_value = first_response

    second_session = mocker.Mock()
    second_session.get.return_value = second_response

    mocker.patch(
        "app.services.activity.fitbit_client.get_fitbit_session",
        side_effect=[first_session, second_session],
    )

    client = FitbitClient()

    import pytest

    with pytest.raises(FitbitAuthError):
        client.get_daily_steps("2026-04-01", "2026-04-01")


def test_raises_rate_limit_error_on_429(mocker):
    response = mocker.Mock()
    response.status_code = 429
    response.text = "Too Many Requests"

    session = mocker.Mock()
    session.get.return_value = response

    mocker.patch(
        "app.services.activity.fitbit_client.get_fitbit_session",
        return_value=session,
    )

    client = FitbitClient()

    import pytest

    with pytest.raises(FitbitRateLimitError):
        client.get_daily_steps("2026-04-01", "2026-04-01")


def test_raises_network_error_on_request_exception(mocker):
    import requests

    session = mocker.Mock()
    session.get.side_effect = requests.exceptions.RequestException("Connection error")

    mocker.patch(
        "app.services.activity.fitbit_client.get_fitbit_session",
        return_value=session,
    )

    client = FitbitClient()

    import pytest

    with pytest.raises(FitbitNetworkError):
        client.get_daily_steps("2026-04-01", "2026-04-01")
