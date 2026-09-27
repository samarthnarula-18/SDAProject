"""
openweather_client.py
-----------------------
Client for the OpenWeather Air Pollution API.

Docs: https://openweathermap.org/api/air-pollution
Endpoint: http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={key}

Note: OpenWeather's own "aqi" field is on a 1-5 scale (European-style
qualitative index), NOT the 0-500 US EPA scale used elsewhere in this
project. So this client ignores OpenWeather's aqi field and instead
computes a US-EPA-style AQI from the returned PM2.5 concentration, using
the same breakpoint table as generate_sample_data.py, to keep every
source in this project comparable.
"""

from datetime import datetime, timezone

import requests

from config import require_openweather_key

BASE_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

CITIES = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Gurugram": (28.4595, 77.0266),
    "Bengaluru": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
}

AQI_BREAKPOINTS = [
    (0.0, 12.0, 0, 50, "Good"),
    (12.1, 35.4, 51, 100, "Moderate"),
    (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, 151, 200, "Unhealthy"),
    (150.5, 250.4, 201, 300, "Very Unhealthy"),
    (250.5, 500.4, 301, 500, "Hazardous"),
]


def pm25_to_aqi(pm25: float):
    if pm25 is None:
        return None, "Unknown"
    for lo_c, hi_c, lo_aqi, hi_aqi, category in AQI_BREAKPOINTS:
        if lo_c <= pm25 <= hi_c:
            aqi = ((hi_aqi - lo_aqi) / (hi_c - lo_c)) * (pm25 - lo_c) + lo_aqi
            return round(aqi), category
    return 500, "Hazardous"


def fetch_city_aqi(city: str, lat: float, lon: float, timeout: int = 10):
    key = require_openweather_key()
    params = {"lat": lat, "lon": lon, "appid": key}
    resp = requests.get(BASE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    entries = payload.get("list", [])
    if not entries:
        print(f"No OpenWeather data returned for {city}.")
        return None

    entry = entries[0]
    components = entry.get("components", {})
    dt_unix = entry.get("dt")
    timestamp = (
        datetime.fromtimestamp(dt_unix, tz=timezone.utc).isoformat()
        if dt_unix
        else datetime.now(timezone.utc).isoformat()
    )

    pm25 = components.get("pm2_5")
    aqi, category = pm25_to_aqi(pm25)

    return {
        "timestamp": timestamp,
        "city": city,
        "lat": lat,
        "lon": lon,
        "source": "OpenWeather",
        "pollutants": {
            "pm25": pm25,
            "pm10": components.get("pm10"),
            "no2": components.get("no2"),
            "so2": components.get("so2"),
            "co": components.get("co"),
            "o3": components.get("o3"),
        },
        "aqi": aqi,
        "category": category,
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
    # Quick manual test: python3 openweather_client.py
    for record in fetch_all_cities():
        print(record)
