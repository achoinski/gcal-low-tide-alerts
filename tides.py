import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

# -----------------------
# 1. Configuration
# -----------------------

STATION_ID = "5cebf1de3d0f4a073c4bb943"
TIME_SERIES_CODE = "wlp"
RESOLUTION = "SIXTY_MINUTES"
THRESHOLD = 0.5  # meters for low tide

# -----------------------
# 2. Compute dynamic date range (next 14 days)
# -----------------------
start = datetime.now(timezone.utc)
end = start + timedelta(days=14)

from_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
to_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

# -----------------------
# 3. Build request URL
# -----------------------
BASE_URL = f"https://api-sine.dfo-mpo.gc.ca/api/v1/stations/{STATION_ID}/data"
params = {
    "time-series-code": TIME_SERIES_CODE,
    "from": from_str,
    "to": to_str,
    "resolution": RESOLUTION
}
url = f"{BASE_URL}?{urlencode(params)}"

# -----------------------
# 4. Fetch tide data
# -----------------------
response = requests.get(url)
response.raise_for_status()
events = response.json()

# -----------------------
# 5. Filter low tides
# -----------------------
low_tides = [e for e in events if e["value"] < THRESHOLD]

# -----------------------
# 6. Print results
# -----------------------
print("NEW VERSION WORKING")
if not low_tides:
    print(f"No low tides below {THRESHOLD}m in the next 14 days.")
else:
    print(f"Found {len(low_tides)} low tides below {THRESHOLD}m:")
    for tide in low_tides:
        print(f"{tide['eventDate']} → {tide['value']} m")

