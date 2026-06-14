#!/usr/bin/env python3
"""Replay a JSONL telemetry file into the CPL Kafka topic.

With --measure, records ingest timestamps and joins them against the
``materialised_at`` field written by the n8n pipeline to produce a
``report.json`` with throughput, latency, and semantic-success-rate stats
per scenario. Mirrors the procedure used to produce Table 2 of the paper.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

try:
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover
    print("kafka-python is required: pip install -r data/requirements.txt", file=sys.stderr)
    raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path, help="Path to the JSONL event file.")
    p.add_argument("--topic", default="context-processing-layer-trigger-topic")
    p.add_argument("--broker", default="localhost:9092")
    p.add_argument("--measure", action="store_true",
                   help="Wait for pipeline drain and emit a report JSON.")
    p.add_argument("--report", type=Path, default=Path("report.json"))
    p.add_argument("--mongo-uri", default="mongodb://cpl:cpl@localhost:27017/?authSource=admin")
    p.add_argument("--mongo-db", default="cpl")
    p.add_argument("--timeout", type=int, default=900,
                   help="Per-scenario drain timeout in seconds.")
    return p.parse_args(argv)


def _load_events(path: Path) -> list[dict]:
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _publish(events: list[dict], topic: str, broker: str) -> dict:
    """Publish events to Kafka, returning evidence_id -> publish-time map."""
    producer = KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=10,
    )
    ingested_at: dict[str, float] = {}
    for ev in events:
        eid = _evidence_id(ev)
        ingested_at[eid] = time.time()
        producer.send(topic, ev)
    producer.flush()
    producer.close()
    return ingested_at


def _evidence_id(ev: dict) -> str:
    if "evidence_id" in ev:
        return ev["evidence_id"]
    if "data" in ev and isinstance(ev["data"], dict) and "evidence_id" in ev["data"]:
        return ev["data"]["evidence_id"]
    raise KeyError(f"event lacks evidence_id: {ev}")


def _scenario(ev: dict) -> str:
    if "scenario" in ev:
        return ev["scenario"]
    if "data" in ev and isinstance(ev["data"], dict):
        return ev["data"].get("scenario", "unknown")
    return "unknown"


def _build_report(events: list[dict], ingested_at: dict[str, float], mongo_uri: str, mongo_db: str, timeout: int) -> dict:
    try:
        from pymongo import MongoClient
    except ImportError:
        print("pymongo is required for --measure: pip install pymongo", file=sys.stderr)
        raise

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    enriched = db["enriched_telemetry_raw"]
    raw = db["telemetry_raw"]

    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_scenario[_scenario(ev)].append(ev)

    scenarios_report: dict[str, dict] = {}
    deadline = time.time() + timeout
    for sc, evs in by_scenario.items():
        expected = {_evidence_id(e) for e in evs}
        while time.time() < deadline:
            done_ids = {d.get("evidence_id") for d in enriched.find({"evidence_id": {"$in": list(expected)}}, {"evidence_id": 1})}
            rejected_ids = {d.get("evidence_id") for d in raw.find({"evidence_id": {"$in": list(expected)}, "parseError": True}, {"evidence_id": 1})}
            if expected.issubset(done_ids | rejected_ids):
                break
            time.sleep(2)
        latencies: list[float] = []
        for d in enriched.find({"evidence_id": {"$in": list(expected)}}, {"evidence_id": 1, "materialised_at": 1}):
            eid = d.get("evidence_id")
            mat = d.get("materialised_at")
            ing = ingested_at.get(eid)
            if ing and mat:
                try:
                    mat_ts = mat if isinstance(mat, (int, float)) else _parse_iso(mat)
                    latencies.append(mat_ts - ing)
                except Exception:
                    continue
        total = len(evs)
        materialised = len(done_ids - rejected_ids)
        elapsed_min = ((max(latencies) if latencies else 0) + (time.time() - min(ingested_at[_evidence_id(e)] for e in evs))) / 60 or 1
        scenarios_report[sc] = {
            "events": total,
            "materialised": materialised,
            "rejected": len(rejected_ids),
            "throughput_per_min": round(total / elapsed_min, 1) if elapsed_min else None,
            "avg_latency_s": round(statistics.mean(latencies), 1) if latencies else None,
            "semantic_success_pct": round(100.0 * materialised / total, 1) if total else None,
        }
    return {"scenarios": scenarios_report}


def _parse_iso(value: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    events = _load_events(args.input)
    print(f"Publishing {len(events)} events to {args.topic} on {args.broker} ...")
    ingested_at = _publish(events, args.topic, args.broker)
    print("Publish complete.")
    if args.measure:
        print("Waiting for pipeline to drain and computing report ...")
        report = _build_report(events, ingested_at, args.mongo_uri, args.mongo_db, args.timeout)
        args.report.write_text(json.dumps(report, indent=2))
        print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
