import json
from datetime import datetime, timedelta
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from app.services.activity import fitbit_auth as auth
from app.services.activity.fitbit_exceptions import FitbitAuthError


@pytest.fixture(autouse=True)
def isolated_auth(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, 'TOKEN_PATH', tmp_path / 'tokens.json')
    monkeypatch.setattr(auth, '_pending_flow', None)
    monkeypatch.setattr(auth, '_pending_state', None)
    monkeypatch.setenv('GOOGLE_HEALTH_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_HEALTH_CLIENT_SECRET', 'test-secret')
    monkeypatch.delenv('GOOGLE_HEALTH_REDIRECT_URI', raising=False)


def credentials():
    return Credentials('test-access', refresh_token='test-refresh', token_uri=auth.TOKEN_URL,
                       client_id='test-client', client_secret='test-secret', scopes=auth.SCOPES,
                       expiry=datetime.utcnow() + timedelta(hours=1))


def test_authorization_uses_google_offline_pkce_and_state():
    url = auth.get_authorization_url()
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == 'accounts.google.com'
    assert query['access_type'] == ['offline']
    assert query['prompt'] == ['consent']
    assert query['code_challenge_method'] == ['S256']
    assert query['state'] == [auth._pending_state]
    assert set(query['scope'][0].split()) == set(auth.SCOPES)


def test_missing_configuration(monkeypatch):
    monkeypatch.delenv('GOOGLE_HEALTH_CLIENT_ID')
    with pytest.raises(FitbitAuthError, match='Configure GOOGLE_HEALTH'):
        auth.get_authorization_url()


def test_old_or_missing_tokens_require_new_consent():
    with pytest.raises(FitbitAuthError, match='cannot be reused'):
        auth.get_fitbit_session()
    auth.TOKEN_PATH.write_text(json.dumps({'access_token': 'old', 'refresh_token': 'old'}))
    with pytest.raises(FitbitAuthError):
        auth.get_fitbit_session()


def test_state_mismatch_never_exchanges_code(mocker):
    auth.get_authorization_url()
    fetch = mocker.patch.object(auth._pending_flow, 'fetch_token')
    with pytest.raises(FitbitAuthError, match='did not match'):
        auth.fetch_and_store_token('http://127.0.0.1:8080/?code=test&state=wrong')
    fetch.assert_not_called()
    assert not auth.TOKEN_PATH.exists()


def prepare_flow(mocker, scopes=None, refresh='test-refresh', status=200):
    creds = credentials()
    creds._granted_scopes = scopes
    creds._refresh_token = refresh
    flow = Mock(redirect_uri='http://127.0.0.1:8080/', credentials=creds)
    mocker.patch.object(auth, '_pending_flow', flow)
    mocker.patch.object(auth, '_pending_state', 'test-state')
    session = mocker.patch.object(auth, 'AuthorizedSession').return_value.__enter__.return_value
    session.get.return_value = Mock(status_code=status, json=Mock(return_value={'healthUserId': 'test-id'}))
    return flow


def test_success_verifies_identity_and_stores_private_tokens(mocker):
    flow = prepare_flow(mocker)
    auth.fetch_and_store_token('http://127.0.0.1:8080/?code=test-code&state=test-state')
    flow.fetch_token.assert_called_once_with(code='test-code', timeout=30)
    assert auth.TOKEN_PATH.stat().st_mode & 0o777 == 0o600
    stored = json.loads(auth.TOKEN_PATH.read_text())
    assert stored['refresh_token'] == 'test-refresh'
    assert stored['token_uri'] == auth.TOKEN_URL


@pytest.mark.parametrize('scopes,refresh,status', [([auth.SCOPES[0]], 'refresh', 200),
    (None, None, 200), (None, 'refresh', 400), (None, 'refresh', 403)])
def test_failed_consent_preserves_existing_tokens(mocker, scopes, refresh, status):
    auth.TOKEN_PATH.write_text('existing')
    prepare_flow(mocker, scopes, refresh, status)
    with pytest.raises(FitbitAuthError):
        auth.fetch_and_store_token('http://127.0.0.1:8080/?code=test-code&state=test-state')
    assert auth.TOKEN_PATH.read_text() == 'existing'


def test_token_failure_is_sanitized(mocker):
    flow = prepare_flow(mocker)
    flow.fetch_token.side_effect = RuntimeError('SENSITIVE')
    with pytest.raises(FitbitAuthError) as exc:
        auth.fetch_and_store_token('http://127.0.0.1:8080/?code=test-code&state=test-state')
    assert 'SENSITIVE' not in str(exc.value)


def test_refresh_uses_google_library_and_persists_token(mocker):
    creds = credentials()
    creds.expiry = datetime.utcnow() - timedelta(hours=1)
    session = auth._PersistentSession(creds)
    def refresh(request):
        creds.token = 'refreshed-access'
        creds.expiry = datetime.utcnow() + timedelta(hours=1)
    refresh_mock = mocker.patch.object(creds, 'refresh', side_effect=refresh)
    mocker.patch('requests.sessions.Session.request', return_value=Mock(status_code=200))
    session.get('https://health.googleapis.com/v4/users/me/identity')
    refresh_mock.assert_called_once()
    assert json.loads(auth.TOKEN_PATH.read_text())['token'] == 'refreshed-access'
    assert json.loads(auth.TOKEN_PATH.read_text())['refresh_token'] == 'test-refresh'


def test_refresh_failure_is_sanitized(mocker):
    creds = credentials()
    creds.expiry = datetime.utcnow() - timedelta(hours=1)
    mocker.patch.object(creds, 'refresh', side_effect=RefreshError('SENSITIVE'))
    with pytest.raises(FitbitAuthError) as exc:
        auth._PersistentSession(creds).get('https://health.googleapis.com/v4/users/me/identity')
    assert 'SENSITIVE' not in str(exc.value)


def test_google_exchange_sends_pkce_and_does_not_use_fitbit(mocker):
    import requests
    auth.get_authorization_url()
    flow, state = auth._pending_flow, auth._pending_state
    token_response = requests.Response()
    token_response.status_code = 200
    token_response._content = json.dumps({'access_token': 'test-access',
        'refresh_token': 'test-refresh', 'expires_in': 3600, 'token_type': 'Bearer',
        'scope': ' '.join(auth.SCOPES)}).encode()
    token_response.request = requests.Request('POST', auth.TOKEN_URL).prepare()
    exchange = mocker.patch.object(flow.oauth2session, 'request', return_value=token_response)
    identity = mocker.patch.object(auth, 'AuthorizedSession').return_value.__enter__.return_value
    identity.get.return_value = Mock(status_code=200, json=Mock(return_value={'healthUserId': 'test-id'}))
    auth.fetch_and_store_token(f'http://127.0.0.1:8080/?code=test-code&state={state}')
    assert exchange.call_args.kwargs['url'] == auth.TOKEN_URL
    assert exchange.call_args.kwargs['data']['code_verifier'] == flow.code_verifier
    assert exchange.call_args.kwargs['data']['grant_type'] == 'authorization_code'


def test_401_refreshes_once_then_returns_failure(mocker):
    creds = credentials()
    refresh = mocker.patch.object(creds, 'refresh')
    request = mocker.patch('requests.sessions.Session.request', return_value=Mock(status_code=401))
    response = auth._PersistentSession(creds, max_refresh_attempts=1).get(
        'https://health.googleapis.com/v4/users/me/identity')
    assert response.status_code == 401
    assert request.call_count == 2
    refresh.assert_called_once()
