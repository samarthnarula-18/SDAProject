"""
config.py
---------
Central settings for the whole AQI pipeline. Every script imports from here,
so Kafka/MongoDB details live in exactly one place.

Secrets (API keys, Mongo password) come from the .env file, never from code.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current directory

# ---- Kafka ----
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "transactions-topic")

# ---- MongoDB Atlas ----
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "weather_db")
# Class database is shared, so keep your own collection name (roll no. suffix)
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "aqi_readings")

# ---- API keys ----
WAQI_TOKEN = os.getenv("WAQI_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")


def require_mongo_uri():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")
    return MONGO_URI


def require_waqi_token():
    if not WAQI_TOKEN or WAQI_TOKEN == "your_token_here":
        raise RuntimeError("WAQI_TOKEN is not set in .env.")
    return WAQI_TOKEN


def require_openweather_key():
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "your_key_here":
        raise RuntimeError("OPENWEATHER_API_KEY is not set in .env.")
    return OPENWEATHER_API_KEY


def require_openaq_key():
    if not OPENAQ_API_KEY or OPENAQ_API_KEY == "your_key_here":
        raise RuntimeError("OPENAQ_API_KEY is not set in .env.")
    return OPENAQ_API_KEY
