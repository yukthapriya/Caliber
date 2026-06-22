"""Consumes live inference events from Kafka ('inference-events'), applies the
selective-prediction policy, persists, raises drift alerts, and broadcasts to the
dashboard WebSocket. Fails soft when no broker is configured."""
import os
import json
import asyncio
import logging

from .database import SessionLocal
from . import crud, schemas

log = logging.getLogger("caliber.kafka")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
TOPIC = os.getenv("KAFKA_TOPIC", "inference-events")


def _handle(event: dict):
    db = SessionLocal()
    try:
        if event.get("type") == "drift":
            crud.create_drift_alert(db, int(event["model_version_id"]),
                                    float(event["drift_score"]), float(event.get("threshold", 0.30)))
        else:
            crud.ingest_prediction(db, schemas.PredictionIn(**event["payload"]))
    finally:
        db.close()


async def run_consumer(manager):
    if not KAFKA_BOOTSTRAP:
        log.info("KAFKA_BOOTSTRAP_SERVERS not set; Kafka consumer disabled (REST/WS still active).")
        return
    try:
        from kafka import KafkaConsumer
    except Exception as e:
        log.warning("kafka-python unavailable: %s", e)
        return

    loop = asyncio.get_event_loop()

    def _make():
        return KafkaConsumer(
            TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            auto_offset_reset="latest", consumer_timeout_ms=1000, group_id="caliber",
        )

    try:
        consumer = await loop.run_in_executor(None, _make)
    except Exception as e:
        log.warning("Kafka connect failed (%s): %s", KAFKA_BOOTSTRAP, e)
        return

    log.info("Caliber consumer connected to %s topic=%s", KAFKA_BOOTSTRAP, TOPIC)
    while True:
        batch = await loop.run_in_executor(None, lambda: list(consumer))
        for msg in batch:
            await loop.run_in_executor(None, _handle, msg.value)
            await manager.broadcast(msg.value)
        await asyncio.sleep(0.2)
