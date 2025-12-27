import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from collections import defaultdict

# -----------------------
# Configuration
# -----------------------

STATION_ID = "5cebf1de3d0f4a073c4bb943"
TIME_SERIES_CODE = "wlp"
RESOLUTION = "SIXTY_MINUTES"
THRESHOLD = 0.5  # meters

# -----------------------
# Date range (next 14 days)
# -----------------------

start = datetime.now(timezone.utc)
end = start + timedelta(days=14)

from_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
to_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

# -----------------------
# Build request URL
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
# Fetch tide data
# -----------------------

response = requests.get(url)
response.raise_for_status()
events = response.json()

# -----------------------
# Group by date
# -----------------------

by_date = defaultdict(list)

for e in events:
    event_time = datetime.fromisoformat(e["eventDate"].replace("Z", "+00:00"))
    date_key = event_time.date()  # YYYY-MM-DD
    by_date[date_key].append({
        "time": event_time,
        "value": e["value"]
    })

# -----------------------
# Find daily minimum tides
# -----------------------

daily_low_tides = []

for date, entries in by_date.items():
    lowest = min(entries, key=lambda x: x["value"])
    if lowest["value"] < THRESHOLD:
        daily_low_tides.append({
            "date": date,
            "time": lowest["time"],
            "value": lowest["value"]
        })

# -----------------------
# Print results
# -----------------------

if not daily_low_tides:
    print(f"No daily low tides below {THRESHOLD}m in the next 14 days.")
else:
    print(f"Low tide days (threshold < {THRESHOLD}m):\n")
    for tide in daily_low_tides:
        print(
            f"{tide['date']} → "
            f"{tide['time'].strftime('%H:%M UTC')} "
            f"({tide['value']} m)"
        )
