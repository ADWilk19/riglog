from datetime import date, timedelta
from unittest.mock import Mock

import pytest
import requests

from app.services.activity.fitbit_client import FitbitClient
from app.services.activity.fitbit_exceptions import (
    FitbitAPIError, FitbitAuthError, FitbitNetworkError, FitbitRateLimitError,
)


@pytest.fixture
def client(mocker):
    session = mocker.Mock()
    mocker.patch('app.services.activity.fitbit_client.get_fitbit_session', return_value=session)
    return FitbitClient()


def response(payload, status=200):
    return Mock(status_code=status, json=Mock(return_value=payload))


def daily(day, steps=None):
    point = {'civilStartTime': {'date': {'year': day.year, 'month': day.month, 'day': day.day}}}
    if steps is not None:
        point['steps'] = {'countSum': str(steps)}
    return point


def test_daily_steps_chunks_pages_and_empty_values(client):
    first = date(2026, 1, 1)
    last = first + timedelta(days=90)
    client.session.request.side_effect = [
        response({'rollupDataPoints': [daily(first, 123)], 'nextPageToken': 'next'}),
        response({'rollupDataPoints': [daily(first + timedelta(days=1))]}),
        response({'rollupDataPoints': [daily(last, 456)]}),
    ]
    rows = client.get_daily_steps(first.isoformat(), last.isoformat())
    assert [r['value'] for r in rows] == [123, 0, 456]
    calls = client.session.request.call_args_list
    assert calls[0].args == ('POST', client.BASE_URL + '/dataTypes/steps/dataPoints:dailyRollUp')
    assert calls[0].kwargs['json']['range']['end']['date'] == {'year': 2026, 'month': 4, 'day': 1}
    assert calls[1].kwargs['json']['pageToken'] == 'next'
    assert 'pageToken' not in calls[2].kwargs['json']
    assert calls[2].kwargs['json']['range']['end']['date']['day'] == 2


@pytest.mark.parametrize('resource,field,value,amount', [
    ('steps', 'steps', 'countSum', '42'), ('calories', 'totalCalories', 'kcalSum', 2.5),
])
def test_intraday_rollup_pagination_and_dst(client, resource, field, value, amount):
    client.session.request.side_effect = [
        response({'timeZone': 'Europe/London'}),
        response({'rollupDataPoints': [{'startTime': '2026-10-25T00:00:00Z', field: {value: amount}}],
                  'nextPageToken': 'page2'}),
        response({'rollupDataPoints': [{'startTime': '2026-10-25T01:00:00Z', field: {value: amount}},
                                      {'startTime': '2026-10-25T02:00:00Z'}]}),
    ]
    rows = client.get_intraday_activity(resource, '2026-10-25')
    assert rows == [{'time': '01:00:00', 'value': float(amount) * 2}]
    body = client.session.request.call_args_list[1].kwargs['json']
    assert body['range'] == {'startTime': '2026-10-24T23:00:00+00:00',
                             'endTime': '2026-10-26T00:00:00+00:00'}
    assert body['windowSize'] == '900s'
    assert body['dataSourceFamily'] == client.SOURCE_FAMILY


def test_spring_dst_one_minute_and_empty_data(client):
    client.session.request.side_effect = [response({'timeZone': 'Europe/London'}), response({})]
    assert client.get_intraday_activity('steps', '2026-03-29', '1min') == []
    body = client.session.request.call_args.kwargs['json']
    assert body['windowSize'] == '60s'
    assert body['range']['endTime'] == '2026-03-29T23:00:00+00:00'


@pytest.mark.parametrize('status,error', [(401, FitbitAuthError), (403, FitbitAuthError),
    (410, FitbitAPIError), (429, FitbitRateLimitError), (500, FitbitAPIError)])
def test_errors_do_not_expose_response(client, status, error):
    client.session.request.return_value = response({'secret': 'SENSITIVE'}, status)
    with pytest.raises(error) as exc:
        client.get_daily_steps('2026-01-01', '2026-01-01')
    assert 'SENSITIVE' not in str(exc.value)


def test_network_errors_are_sanitized(client):
    client.session.request.side_effect = requests.RequestException('SENSITIVE')
    with pytest.raises(FitbitNetworkError, match='^Network error contacting Google Health.$'):
        client.get_daily_steps('2026-01-01', '2026-01-01')
