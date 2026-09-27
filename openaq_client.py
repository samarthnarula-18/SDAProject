"""
openaq_client.py
-----------------
Client for the OpenAQ v3 API.

Docs: https://docs.openaq.org/
Auth: header "X-API-Key: <key>"

OpenAQ v3 doesn't let you query "give me AQI for city X" directly like WAQI
does. Instead:
  1. Find the nearest monitoring station (a "location") to a lat/lon via
     GET /v3/locations?coordinates=lat,lon&radius=...
  2. Get that location's sensors (each sensor measures one parameter, e.g.
     pm25) via the "sensors" field already included in the locations response.
  3. Get the latest reading for each sensor at that location via
     GET /v3/locations/{id}/latest

Because live network access to api.openaq.org isn't available in this
build environment, this client is written directly from OpenAQ's current
v3 documentation but hasn't been run end-to-end here — run
`python3 openaq_client.py` yourself to confirm it works with your key
before wiring it into the producer.
"""

from datetime import datetime, timezone

import requests

from config import require_openaq_key

BASE_URL = "https://api.openaq.org/v3"

# City name -> approximate coordinates (lat, lon), matching the other sources
CITIES = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Gurugram": (28.4595, 77.0266),
    "Bengaluru": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
}

SEARCH_RADIUS_METERS = 25000  # 25km


def _headers():
    return {"X-API-Key": require_openaq_key()}


def find_nearest_location(lat: float, lon: float, timeout: int = 10):
    """Return the nearest OpenAQ location record for a coordinate, or None."""
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": SEARCH_RADIUS_METERS,
        "limit": 1,
        "order_by": "distance",
    }
    resp = requests.get(url, headers=_headers(), params=params, timeout=timeout)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


def get_latest_for_location(location_id: int, timeout: int = 10):
    """Return the latest sensor readings for a given location id."""
    url = f"{BASE_URL}/locations/{location_id}/latest"
    resp = requests.get(url, headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("results", [])


def fetch_city_aqi(city: str, lat: float, lon: float):
    """Find the nearest station to a city and return a normalized record, or None."""
    location = find_nearest_location(lat, lon)
    if not location:
        print(f"No OpenAQ station found near {city}.")
        return None

    location_id = location["id"]
    sensor_param_map = {
        s["id"]: s["parameter"]["name"] for s in location.get("sensors", [])
    }

    latest = get_latest_for_location(location_id)
    if not latest:
        print(f"No latest readings available for {city} (station {location_id}).")
        return None

    pollutants = {}
    latest_ts = None
    for reading in latest:
        param = sensor_param_map.get(reading.get("sensorsId"))
        if param:
            pollutants[param] = reading.get("value")
        if reading.get("datetime", {}).get("utc"):
            latest_ts = reading["datetime"]["utc"]

    return {
        "timestamp": latest_ts or datetime.now(timezone.utc).isoformat(),
        "city": city,
        "lat": lat,
        "lon": lon,
        "source": "OpenAQ",
        "pollutants": {
            "pm25": pollutants.get("pm25"),
            "pm10": pollutants.get("pm10"),
            "no2": pollutants.get("no2"),
            "so2": pollutants.get("so2"),
            "co": pollutants.get("co"),
            "o3": pollutants.get("o3"),
        },
        # OpenAQ gives raw pollutant concentrations, not a precomputed AQI —
        # compute it downstream from pm25 the same way the sample data does.
    }


def fetch_all_cities():
    results = []
    for city, (lat, lon) in CITIES.items():
        try:
            record = fetch_city_aqi(city, lat, lon)
            if record:
                results.append(record)
        except requests.RequestException as e:
            print(f"Request failed for '{city}': {e}")
    return results


if __name__ == "__main__":
    # Quick manual test: python3 openaq_client.py
    for record in fetch_all_cities():
        print(record)
