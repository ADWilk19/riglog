from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Any

import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

AUTH_BASE_URL = "https://www.fitbit.com/oauth2/authorize"
TOKEN_URL = "https://api.fitbit.com/oauth2/token"
TOKEN_PATH = PROJECT_ROOT / "data" / "fitbit_tokens.json"

# local dev only
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


def _token_updater(token: dict[str, Any]) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2))


def get_fitbit_session() -> OAuth2Session:
    client_id = os.environ["FITBIT_CLIENT_ID"]
    client_secret = os.environ["FITBIT_CLIENT_SECRET"]
    redirect_uri = os.environ.get("FITBIT_REDIRECT_URI", "http://127.0.0.1:8080/")

    token = None

    if TOKEN_PATH.exists():
        token = json.loads(TOKEN_PATH.read_text())

        if "refresh_token" not in token:
            token = None

    return OAuth2Session(
        client_id=client_id,
        token=token,
        redirect_uri=redirect_uri,
        scope=["activity", "profile"],
        auto_refresh_url=TOKEN_URL,
        auto_refresh_kwargs={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        token_updater=_token_updater,
    )


def get_authorization_url() -> str:
    client_id = os.environ["FITBIT_CLIENT_ID"]
    redirect_uri = os.environ.get("FITBIT_REDIRECT_URI", "http://127.0.0.1:8080/")

    session = OAuth2Session(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=["activity", "profile"],
    )
    auth_url, _ = session.authorization_url(AUTH_BASE_URL)
    return auth_url


def fetch_and_store_token(authorization_response_url: str) -> None:
    client_id = os.environ["FITBIT_CLIENT_ID"]
    client_secret = os.environ["FITBIT_CLIENT_SECRET"]
    redirect_uri = os.environ.get("FITBIT_REDIRECT_URI", "http://127.0.0.1:8080/")

    # Parse the code out of the redirect URL
    session = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri)
    parsed = session._client.parse_request_uri_response(authorization_response_url)
    code = parsed["code"]

    response = requests.post(
        TOKEN_URL,
        auth=HTTPBasicAuth(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=30,
    )
    response.raise_for_status()

    token = response.json()

    if "access_token" not in token:
        raise RuntimeError(f"Fitbit token response did not contain access_token: {token}")

    _token_updater(token)
