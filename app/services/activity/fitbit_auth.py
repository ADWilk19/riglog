"""Google OAuth for Fitbit data; legacy Fitbit tokens cannot be migrated."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dotenv import load_dotenv
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.services.activity.fitbit_exceptions import FitbitAuthError, FitbitNetworkError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")
AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_PATH = PROJECT_ROOT / "data" / "google_health_tokens.json"
SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.settings.readonly",
]
_pending_flow = None
_pending_state = None


def _token_updater(credentials: Credentials) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=TOKEN_PATH.parent, prefix=".google-health-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(credentials.to_json())
        os.replace(name, TOKEN_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class _PersistentSession(AuthorizedSession):
    def request(self, *args, **kwargs):
        previous = self.credentials.token
        try:
            return super().request(*args, **kwargs)
        except RefreshError:
            raise FitbitAuthError("Reconnect Fitbit through Google Health to renew access.") from None
        except TransportError:
            raise FitbitNetworkError("Network error contacting Google Health.") from None
        finally:
            if self.credentials.token != previous:
                _token_updater(self.credentials)


def get_fitbit_session() -> AuthorizedSession:
    try:
        info = json.loads(TOKEN_PATH.read_text())
        # Never load the retired Fitbit token file or trust a stored token endpoint.
        if not set(SCOPES).issubset(info.get("scopes", [])):
            raise ValueError("Missing scopes")
        credentials = Credentials.from_authorized_user_info(info)
        if not credentials.refresh_token:
            raise ValueError("Missing refresh token")
    except (OSError, ValueError, TypeError):
        raise FitbitAuthError(
            "Fitbit's old API has shut down. Connect through Google Health; "
            "existing Fitbit tokens cannot be reused. See docs/google-health-setup.md."
        ) from None
    return _PersistentSession(credentials, max_refresh_attempts=1)


def get_authorization_url() -> str:
    global _pending_flow, _pending_state
    client_id = os.getenv("GOOGLE_HEALTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_HEALTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise FitbitAuthError(
            "Configure GOOGLE_HEALTH_CLIENT_ID and GOOGLE_HEALTH_CLIENT_SECRET "
            "with a Google Desktop app OAuth client. See docs/google-health-setup.md."
        )
    redirect_uri = os.getenv("GOOGLE_HEALTH_REDIRECT_URI", "http://127.0.0.1:8080/")
    redirect = urlsplit(redirect_uri)
    if redirect.scheme != "http" or redirect.hostname != "127.0.0.1" or redirect.query or redirect.fragment:
        raise FitbitAuthError("Use a local http://127.0.0.1 loopback redirect URI.")
    _pending_flow = Flow.from_client_config(
        {"installed": {"client_id": client_id, "client_secret": client_secret,
                       "auth_uri": AUTH_BASE_URL, "token_uri": TOKEN_URL,
                       "redirect_uris": [redirect_uri]}},
        scopes=SCOPES, redirect_uri=redirect_uri, autogenerate_code_verifier=True,
    )
    url, _pending_state = _pending_flow.authorization_url(
        access_type="offline", prompt="consent",
    )
    return url


def fetch_and_store_token(authorization_response_url: str) -> None:
    global _pending_flow, _pending_state
    flow, state = _pending_flow, _pending_state
    _pending_flow = _pending_state = None
    if flow is None or state is None:
        raise FitbitAuthError("Start a new connection before submitting the redirect URL.")
    parsed = urlsplit(authorization_response_url)
    expected = urlsplit(flow.redirect_uri)
    query = parse_qs(parsed.query)
    if ((parsed.scheme, parsed.netloc, parsed.path) !=
            (expected.scheme, expected.netloc, expected.path)
            or parsed.fragment or len(query.get("state", [])) != 1
            or not secrets.compare_digest(query["state"][0], state)):
        raise FitbitAuthError("Connection response did not match. Start a new connection.")
    if "error" in query or len(query.get("code", [])) != 1:
        raise FitbitAuthError("Access was not granted. Start a new connection and approve access.")
    try:
        # Validate state ourselves so loopback HTTP doesn't require disabling HTTPS checks.
        flow.fetch_token(code=query["code"][0], timeout=30)
        credentials = flow.credentials
        granted = credentials.granted_scopes or credentials.scopes or []
        if not set(SCOPES).issubset(granted) or not credentials.refresh_token:
            raise FitbitAuthError("Approve activity and settings access for offline syncing.")
        with AuthorizedSession(credentials) as session:
            response = session.get("https://health.googleapis.com/v4/users/me/identity", timeout=20)
        if response.status_code == 400:
            raise FitbitAuthError("Sign in to the Google Health mobile app and link your account, then reconnect.")
        if response.status_code != 200 or not response.json().get("healthUserId"):
            raise FitbitAuthError("Could not verify Google Health access. Check API setup and permissions.")
        _token_updater(credentials)
    except FitbitAuthError:
        raise
    except Exception:
        # OAuth exceptions may contain codes, tokens, or provider response bodies.
        raise FitbitAuthError("Google Health connection failed. Start a new connection and try again.") from None
