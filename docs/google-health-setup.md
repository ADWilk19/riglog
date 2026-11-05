# Fitbit connection through Google Health

The Fitbit Web API and Fitbit OAuth were switched off on **2 November 2026**.
HTTP 410 from `https://api.fitbit.com/oauth2/token` means the service has been
retired. Retrying, resetting the Python environment, or reusing Fitbit credentials
cannot restore it.

## One-time setup

1. In Google Cloud Console, create/select a project and enable **Google Health API**.
2. Configure the OAuth consent screen, audience and test users as appropriate.
   Request these read-only scopes:
   - `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
   - `https://www.googleapis.com/auth/googlehealth.settings.readonly`
   Settings access supplies the account timezone for intraday activity.
   Follow Google's access/verification requirements for restricted Health scopes.
3. Create an OAuth client of type **Desktop app**. Put its values in your local
   `.env` using `GOOGLE_HEALTH_CLIENT_ID` and `GOOGLE_HEALTH_CLIENT_SECRET`.
   Do not reuse `FITBIT_CLIENT_ID` or `FITBIT_CLIENT_SECRET`.
   The default loopback redirect is `http://127.0.0.1:8080/`;
   `GOOGLE_HEALTH_REDIRECT_URI` may override its port/path.
4. Install the updated requirements in your RigLog environment:
   `python -m pip install -r requirements.txt`.
5. Ensure your Google Account is linked in the Google Health mobile app.
   In RigLog choose **Refresh → Reconnect Fitbit**, sign in with that account,
   and approve both permissions. The local redirect page may show a connection
   error because this existing manual flow does not run a web server. Copy the
   complete address from the browser into RigLog's dialog. Never share it in logs,
   chat, or screenshots. Alternatively run `python -m scripts.fitbit_auth_setup`
   from the repository root.
6. Refresh activity again if needed. For a live smoke test, sync one known day
   and compare steps and total calories against Google Health.

The new token file is `data/google_health_tokens.json`, ignored by Git and written
atomically with owner-only permissions. Old `data/fitbit_tokens.json` is never read
or sent to Google. No code path syncs from the retired Fitbit API. Existing activity
records retain their `fitbit` source so reimporting updates them instead of creating
another source. Existing databases and credentials need not be deleted.

OAuth consent is mandatory: Fitbit access/refresh tokens cannot be transferred.
Google refresh tokens are retained when refreshing access tokens. Testing-mode
consent can expire; see Google's current OAuth rules if reconnection is repeatedly
needed. The app verifies Google Health identity before saving a new connection.

## Data behavior and limitations

Daily steps use calendar-day `dailyRollUp` queries, split into at most 90-day ranges.
Intraday steps and total calories use 1- or 15-minute `rollUp` queries in the
account's current IANA timezone. The `google-sources` family includes Google/Fitbit
wearables and other first-party sources; it may differ from legacy Fitbit totals.
Pagination is followed. Missing intraday measurements remain missing.

RigLog's existing intraday schema stores local timestamps without timezone offsets.
Repeated wall-clock buckets on the autumn DST transition are combined to preserve
totals. Historical travel cannot be represented precisely in that schema: intraday
backfills use the account's current timezone, while daily totals use Google's civil
calendar-day aggregation. No database migration is included in this fix.

Automated tests use synthetic responses and never contact a real account. A passing
test suite verifies the adapter and OAuth behavior, not Google Cloud enrollment or
live user consent.

## Official references (checked 5 November 2026)

- [Shutdown date and HTTP 410](https://developers.google.com/health/about)
- [OAuth migration, app registration and mandatory consent](https://developers.google.com/health/migration/data-access)
- [Migration and identity verification](https://developers.google.com/health/migration)
- [Aggregation and range limits](https://developers.google.com/health/aggregate-data)
- [Daily rollup reference](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp)
- [Intraday rollup reference](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/rollUp)
- [Account timezone](https://developers.google.com/health/reference/rest/v4/Settings)
