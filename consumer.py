"""
consumer.py
------------
Consumer for the AQI streaming pipeline (Assignment 3):

    Topic: aqi_data -> Consumer (this script) -> MongoDB -> Dashboard

Reads every message from the 'aqi_data' Kafka topic, does light cleaning /
validation, and writes each reading into MongoDB so the dashboard
(dashboard.py) has something to query and chart.

Usage:
    python3 consumer.py
    python3 consumer.py --broker localhost:9092 --mongo-uri mongodb://localhost:27017
"""

import argparse
import json

from kafka import KafkaConsumer
from pymongo import MongoClient

TOPIC_NAME = "aqi_data"
DB_NAME = "aqi_pipeline"
COLLECTION_NAME = "readings"


def build_consumer(broker: str) -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[broker],
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="aqi-mongo-writer",
    )


def is_valid(record: dict) -> bool:
    """Basic data-quality check before writing to MongoDB."""
    required_fields = ["timestamp", "city", "pollutants", "aqi", "category"]
    if not all(field in record for field in required_fields):
        return False
    if record["aqi"] is None:
        return False
    pm25 = record.get("pollutants", {}).get("pm25")
    if pm25 is None or pm25 < 0:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Consume AQI data from Kafka into MongoDB.")
    parser.add_argument("--broker", default="localhost:9092", help="Kafka bootstrap server")
    parser.add_argument(
        "--mongo-uri", default="mongodb://localhost:27017", help="MongoDB connection URI"
    )
    args = parser.parse_args()

    print(f"Connecting to Kafka broker at {args.broker} ...")
    consumer = build_consumer(args.broker)

    print(f"Connecting to MongoDB at {args.mongo_uri} ...")
    mongo_client = MongoClient(args.mongo_uri)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]

    print(
        f"Listening on topic '{TOPIC_NAME}', writing valid records to "
        f"{DB_NAME}.{COLLECTION_NAME}. Press Ctrl+C to stop.\n"
    )

    received, written, rejected = 0, 0, 0

    try:
        for message in consumer:
            received += 1
            record = message.value

            if not is_valid(record):
                rejected += 1
                print(f"Rejected malformed/incomplete record: {record}")
                continue

            collection.insert_one(record)
            written += 1
            print(
                f"[offset={message.offset}] Stored -> city={record['city']} "
                f"aqi={record['aqi']} ({record['category']}) "
                f"| received={received} written={written} rejected={rejected}"
            )
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        consumer.close()
        mongo_client.close()
        print(f"\nDone. received={received} written={written} rejected={rejected}")


if __name__ == "__main__":
    main()
