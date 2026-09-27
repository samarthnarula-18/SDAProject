"""
config.py
---------
Loads API credentials from a .env file (never hardcode keys in source).

Copy .env.example to .env and fill in your real keys before running the
live producer. This project ships a real .env for OpenAQ + OpenWeather —
treat it as a secret file, don't commit or share it further.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current directory

WAQI_TOKEN = os.getenv("WAQI_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")


def require_waqi_token():
    if not WAQI_TOKEN or WAQI_TOKEN == "your_token_here":
        raise RuntimeError(
            "WAQI_TOKEN is not set. Copy .env.example to .env and paste your "
            "free token from https://aqicn.org/data-platform/token/"
        )
    return WAQI_TOKEN


def require_openweather_key():
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "your_key_here":
        raise RuntimeError(
            "OPENWEATHER_API_KEY is not set. Add it to your .env file. "
            "Get one at https://openweathermap.org/api/air-pollution"
        )
    return OPENWEATHER_API_KEY


def require_openaq_key():
    if not OPENAQ_API_KEY or OPENAQ_API_KEY == "your_key_here":
        raise RuntimeError(
            "OPENAQ_API_KEY is not set. Add it to your .env file. "
            "Get one at https://explore.openaq.org/register"
        )
    return OPENAQ_API_KEY
