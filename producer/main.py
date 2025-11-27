import json
import os
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "synthetic_users")

app = FastAPI(title="Kafka Producer Service")


class RecordsPayload(BaseModel):
    records: List[dict]


def create_producer():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=5,
        max_in_flight_requests_per_connection=5,
    )
    return producer


producer = None


def get_producer():
    global producer
    if producer is not None:
        return producer

    try:
        producer = create_producer()
        print("Kafka producer created successfully")
    except Exception as e:
        # Не падаем, но вернём 503 из хендлера
        print(f"Failed to create Kafka producer: {e}")
        producer = None

    return producer


@app.post("/produce")
async def produce(payload: RecordsPayload):
    local_producer = get_producer()
    if local_producer is None:
        raise HTTPException(status_code=503, detail="Kafka producer is not available")

    errors = 0
    for record in payload.records:
        try:
            local_producer.send(KAFKA_TOPIC, record)
        except Exception as e:
            errors += 1
            print(f"Error sending record to Kafka: {e}")

    try:
        local_producer.flush(timeout=10)
    except Exception as e:
        print(f"Error flushing Kafka producer: {e}")
        raise HTTPException(status_code=503, detail="Failed to flush messages to Kafka")

    return {"sent": len(payload.records), "errors": errors}
