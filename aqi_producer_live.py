"""
aqi_producer_live.py
---------------------
Live Kafka producer that pulls real AQI data from TWO sources — OpenAQ and
OpenWeather — on a fixed interval and streams every reading to the
'aqi_data' Kafka topic.

Requires real API keys in .env (see .env / .env.example).

Usage:
    python3 aqi_producer_live.py
    python3 aqi_producer_live.py --interval 60 --broker localhost:9092
"""

import argparse
import json
import time
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

import openaq_client
import openweather_client
from openweather_client import pm25_to_aqi

from config import TOPIC as TOPIC_NAME, KAFKA_BROKER


def build_producer(broker: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        retries=3,
        acks="all",
    )


def collect_records():
    """Pull the latest readings from both sources and merge into one list."""
    records = []

    try:
        openaq_records = openaq_client.fetch_all_cities()
        # OpenAQ doesn't return a precomputed AQI — derive it from pm25
        for r in openaq_records:
            aqi, category = pm25_to_aqi(r["pollutants"].get("pm25"))
            r["aqi"] = aqi
            r["category"] = category
        records.extend(openaq_records)
    except Exception as e:
        print(f"OpenAQ fetch failed this cycle: {e}")

    try:
        records.extend(openweather_client.fetch_all_cities())
    except Exception as e:
        print(f"OpenWeather fetch failed this cycle: {e}")

    return records


def poll_and_send(producer: KafkaProducer):
    records = collect_records()

    if not records:
        print("No records returned this cycle (API error or no data).")
        return

    for record in records:
        try:
            future = producer.send(TOPIC_NAME, key=record["city"], value=record)
            metadata = future.get(timeout=10)
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(
                f"[{now}] Sent -> topic={metadata.topic} "
                f"partition={metadata.partition} offset={metadata.offset} "
                f"| source={record['source']} city={record['city']} "
                f"aqi={record.get('aqi')} ({record.get('category')})"
            )
        except KafkaError as e:
            print(f"ERROR sending record for {record['city']}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Stream live OpenAQ + OpenWeather data to Kafka.")
    parser.add_argument("--broker", default=KAFKA_BROKER, help="Kafka bootstrap server")
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Seconds between polling cycles"
    )
    args = parser.parse_args()

    print(f"Connecting to Kafka broker at {args.broker} ...")
    producer = build_producer(args.broker)

    print(
        f"Polling OpenAQ + OpenWeather every {args.interval}s and streaming "
        f"to topic '{TOPIC_NAME}'. Press Ctrl+C to stop.\n"
    )

    try:
        while True:
            poll_and_send(producer)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
