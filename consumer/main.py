import json
import os
import time
from datetime import datetime
from typing import Optional

import psycopg2
from kafka import KafkaConsumer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "synthetic_users")

PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB", "synthetic_db")
PG_USER = os.getenv("POSTGRES_USER", "synthetic_user")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "synthetic_pass")


def validate_str(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    value = str(value)
    if len(value) > max_len:
        return value[:max_len]
    return value


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def main():
    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                group_id="synthetic-consumers",
            )
            break
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}, retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            conn = get_pg_conn()
            conn.autocommit = True
            cursor = conn.cursor()
            break
        except Exception as e:
            print(f"Failed to connect to Postgres: {e}, retrying in 5 seconds...")
            time.sleep(5)

    print("Consumer started. Waiting for messages...")

    for msg in consumer:
        payload = msg.value
        error = None

        try:
            name = validate_str(payload.get("name"), 255)
            email = validate_str(payload.get("email"), 255)
            event_time = parse_datetime(payload.get("date"))
            password_hash = validate_str(payload.get("password_hash"), 128)
            country = validate_str(payload.get("country"), 128)
            city = validate_str(payload.get("city"), 128)
            phone_number = validate_str(payload.get("phone_number"), 64)
            job = validate_str(payload.get("job"), 255)
            company = validate_str(payload.get("company"), 255)
            ipv4 = validate_str(payload.get("ipv4"), 45)
        except Exception as e:
            error = f"Validation error: {e}"

        try:
            cursor.execute(
                """
                INSERT INTO users_raw (
                    name, email, event_time, password_hash,
                    country, city, phone_number, job, company, ipv4,
                    raw_payload, error
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    name,
                    email,
                    event_time,
                    password_hash,
                    country,
                    city,
                    phone_number,
                    job,
                    company,
                    ipv4,
                    json.dumps(payload),
                    error,
                ],
            )
        except Exception as e:
            print(f"Failed to insert into users_raw: {e}")


if __name__ == "__main__":
    main()
