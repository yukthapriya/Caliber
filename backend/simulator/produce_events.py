"""Streams live inference events (and rising drift) so Caliber's dashboard shows
real-time monitoring + a growing review queue. Uses Kafka if configured, else POSTs
the REST API.  python simulator/produce_events.py"""
import os, json, time, random

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
TOPIC = os.getenv("KAFKA_TOPIC", "inference-events")
API = os.getenv("API_URL", "http://localhost:8000")
MV_ID = int(os.getenv("MODEL_VERSION_ID", "1"))


def _event(step):
    conf = random.uniform(0.5, 0.98)
    correct = random.random() < (conf - 0.05)
    return {"type": "prediction", "payload": {
        "model_version_id": MV_ID, "sample_id": f"live-{step}",
        "predicted_label": "pos", "confidence": round(conf, 3),
        "uncertainty": round(1 - conf, 3),
        "ground_truth": ("pos" if correct else "neg") if random.random() < 0.5 else None,
    }}


def _drift(step):
    return {"type": "drift", "model_version_id": MV_ID,
            "drift_score": round(min(0.6, 0.1 + step * 0.01), 3), "threshold": 0.30}


def via_kafka():
    from kafka import KafkaProducer
    p = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                      value_serializer=lambda v: json.dumps(v).encode())
    print(f"Producing inference events to Kafka '{TOPIC}' ...")
    step = 0
    while True:
        p.send(TOPIC, _event(step))
        if step % 20 == 19:
            p.send(TOPIC, _drift(step))
        p.flush(); step += 1; time.sleep(0.5)


def via_rest():
    import urllib.request
    print(f"No Kafka broker; POSTing predictions to {API}/api/predictions ...")
    step = 0
    while True:
        body = json.dumps(_event(step)["payload"]).encode()
        req = urllib.request.Request(f"{API}/api/predictions", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=2).read()
        except Exception as e:
            print("post failed:", e)
        step += 1; time.sleep(0.5)


if __name__ == "__main__":
    (via_kafka if KAFKA_BOOTSTRAP else via_rest)()
