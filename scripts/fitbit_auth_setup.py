from app.services.activity.fitbit_auth import (
    get_authorization_url,
    fetch_and_store_token,
)

print("Open this URL in your browser:\n")
print(get_authorization_url())
print("\nAfter approving, paste the full redirect URL below:\n")
redirect_url = input("> ").strip()

fetch_and_store_token(redirect_url)
print("Token saved to data/fitbit_tokens.json")
