"""
consumer.py
------------
Consumer for the AQI streaming pipeline (Assignment 3):

    Kafka topic -> Consumer (this script) -> MongoDB Atlas -> Dashboard

Reads every message from the Kafka topic, validates it, and writes valid
readings into MongoDB Atlas so dashboard.py can query and chart them.

Usage:
    python3 consumer.py
"""

import argparse
import json

from kafka import KafkaConsumer
from pymongo import MongoClient

from config import (
    KAFKA_BROKER, TOPIC, DB_NAME, COLLECTION_NAME, require_mongo_uri,
)


def build_consumer(broker: str) -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=[broker],
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="aqi-atlas-writer",
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
    parser = argparse.ArgumentParser(description="Consume AQI data from Kafka into MongoDB Atlas.")
    parser.add_argument("--broker", default=KAFKA_BROKER, help="Kafka bootstrap server")
    args = parser.parse_args()

    print(f"Connecting to Kafka broker at {args.broker} ...")
    consumer = build_consumer(args.broker)

    print("Connecting to MongoDB Atlas ...")
    mongo_client = MongoClient(require_mongo_uri(), serverSelectionTimeoutMS=15000)
    mongo_client.admin.command("ping")  # fail fast if Atlas is unreachable
    collection = mongo_client[DB_NAME][COLLECTION_NAME]
    print("Atlas connection OK.")

    print(
        f"Listening on topic '{TOPIC}', writing valid records to "
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
