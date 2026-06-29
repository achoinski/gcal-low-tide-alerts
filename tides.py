import os
import json
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from collections import defaultdict
from datetime import datetime
import re


# =======================
# CONFIGURATION
# =======================

STATION_ID = "5cebf1de3d0f4a073c4bb943"
TIME_SERIES_CODE = "wlp"
RESOLUTION = "SIXTY_MINUTES"
THRESHOLD = 0.5  # meters

CALENDAR_ID = "50479ca776433aa9a20dbdcd277896af1291ac8630e598f8ba7075640c5e512a@group.calendar.google.com"
TIMEZONE = "America/Vancouver"

DRY_RUN = False  # ← set to True to test without creating events

# =======================
# DATE RANGE (4 weeks)
# =======================

start = datetime.now(timezone.utc)
end = start + timedelta(days=28)

from_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
to_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

# =======================
# FETCH TIDE DATA
# =======================

BASE_URL = f"https://api-sine.dfo-mpo.gc.ca/api/v1/stations/{STATION_ID}/data"
params = {
    "time-series-code": TIME_SERIES_CODE,
    "from": from_str,
    "to": to_str,
    "resolution": RESOLUTION,
}

url = f"{BASE_URL}?{urlencode(params)}"

response = requests.get(url)
response.raise_for_status()
events = response.json()

for tide in events:
    # Convert the eventDate string to a datetime object (UTC)
    tide['time'] = datetime.fromisoformat(tide['eventDate'].replace("Z", "+00:00"))

# =======================
# GROUP BY DATE
# =======================

by_date = defaultdict(list)

for e in events:
    t = datetime.fromisoformat(e["eventDate"].replace("Z", "+00:00"))
    by_date[t.date()].append({"time": t, "value": e["value"]})

# =======================
# DAILY LOW TIDES
# =======================

daily_low_tides = []

for date, entries in by_date.items():
    lowest = min(entries, key=lambda x: x["value"])
    if lowest["value"] < THRESHOLD:
        daily_low_tides.append({
            "date": date,
            "time": lowest["time"],
            "value": lowest["value"],
        })

if not daily_low_tides:
    print("No low tides below threshold.")
    exit(0)

# =======================
# GOOGLE CALENDAR SETUP
# =======================

if not DRY_RUN:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError


    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"]),
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    service = build("calendar", "v3", credentials=creds)


# =======================
# CREATE CALENDAR EVENTS (with duplicate checking)
# =======================

from googleapiclient.errors import HttpError

# Build a set of dates that already have events
existing_events = set()
if not DRY_RUN:
    for tide in daily_low_tides:
        # start and end of the day in UTC
        day_start = tide['time'].replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        day_end = day_start + timedelta(days=1)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True
        ).execute()

        for e in events_result.get('items', []):
            existing_events.add(day_start.date())

# Loop through daily low tides and insert events if not already present
for tide in daily_low_tides:
    if tide['date'] in existing_events:
        print(f"Skipped {tide['date']} (already exists)")
        continue

    local_time = tide["time"].astimezone(
        timezone(timedelta(hours=-7))  # PST/PDT for display
    )

    start_time = tide["time"].isoformat()
    end_time = (tide["time"] + timedelta(hours=1)).isoformat()

    title = f"Low tide {tide['value']} m at {local_time.strftime('%H:%M')}"
    description = (
        f"Lowest predicted tide of the day\n"
        f"Height: {tide['value']} m\n"
        f"Time (UTC): {tide['time'].strftime('%H:%M')}"
    )

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }

    if DRY_RUN:
        print(f"[DRY RUN] Would create event: {title}")
    else:
        try:
            service.events().insert(
                calendarId=CALENDAR_ID,
                body=event,
            ).execute()
            print(f"Created event: {title}")
        except HttpError as e:
            print("Google Calendar error:")
            print(e)
            raise
