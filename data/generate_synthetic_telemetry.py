#!/usr/bin/env python3
# Keep the noisy/heartbeat event ratio constant across scenarios so agent count
# is not confounded with workload cleanliness in the semantic-success evaluation.
"""Generate synthetic multi-agent telemetry for the CPL feasibility evaluation.

Reproduces the corpus described in the paper:
  - three scenarios: single-agent, two-agent, three-agent
  - 60 interaction-event sequences per scenario by default
  - heterogeneous event shapes (key-value, nested, free-text annotations)
  - deterministic given --seed

Output is JSON Lines on stdout or to --out, one event per line, ready to be
fed into ``scripts/publish_to_kafka.py``.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SCENARIOS = ("single", "two", "three")
DEFAULT_NOISE_RATIO = 0.25

TOOLS = [
    "student_record_api",
    "financial_check_service",
    "application_portal_client",
    "audit_log_writer",
    "transcript_parser",
]

DATA_ENTITIES = [
    "student_profile",
    "transcript",
    "financial_record",
    "application_form",
    "scholarship_eligibility",
]

NOISY_HEARTBEAT_KINDS = ("heartbeat", "ack", "status_ping", "keepalive")


@dataclass
class Scenario:
    name: str
    agents: list[str]
    events_per_sequence: int
    noisy_ratio: float  # share of heartbeat / introspective events
    sequences: int = 60


def build_scenarios(per_scenario: int, noise_ratio: float = DEFAULT_NOISE_RATIO) -> list[Scenario]:
    return [
        Scenario(
            name="single",
            agents=["retrieval_agent"],
            events_per_sequence=4,
            noisy_ratio=noise_ratio,
            sequences=per_scenario,
        ),
        Scenario(
            name="two",
            agents=["retrieval_agent", "financial_agent"],
            events_per_sequence=6,
            noisy_ratio=noise_ratio,
            sequences=per_scenario,
        ),
        Scenario(
            name="three",
            agents=["retrieval_agent", "financial_agent", "portal_agent"],
            events_per_sequence=8,
            noisy_ratio=noise_ratio,
            sequences=per_scenario,
        ),
    ]


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_id(rng: random.Random) -> str:
    return f"evt:{rng.getrandbits(32):08x}"


def _maybe_nested(rng: random.Random, payload: dict) -> dict:
    # Vary shape: sometimes flat, sometimes nested under "data".
    if rng.random() < 0.4:
        return {"data": payload, "envelope_version": "1.0"}
    return payload


def _make_noisy_event(rng: random.Random, scenario: Scenario, ts: datetime, run: int) -> dict:
    kind = rng.choice(NOISY_HEARTBEAT_KINDS)
    return {
        "evidence_id": _event_id(rng),
        "scenario": scenario.name,
        "run": run,
        "kind": kind,
        "ts": _iso(ts),
        "note": rng.choice([
            "ok",
            "still alive",
            "no change",
            "queue empty",
            "",
        ]),
    }


def _make_action_event(
    rng: random.Random,
    scenario: Scenario,
    ts: datetime,
    run: int,
    actor: str,
    target: str | None,
) -> dict:
    tool = rng.choice(TOOLS)
    data_entity = rng.choice(DATA_ENTITIES)
    payload = {
        "evidence_id": _event_id(rng),
        "scenario": scenario.name,
        "run": run,
        "kind": "agent_action",
        "ts": _iso(ts),
        "actor": actor,
        "tool": tool,
        "accessed_data": data_entity,
        "target_agent": target,
        "free_text": rng.choice([
            f"{actor} invoked {tool} on {data_entity}",
            f"delegating {data_entity} retrieval to {target}" if target else f"local {tool} call",
            "",
        ]),
    }
    return _maybe_nested(rng, payload)


def generate_scenario(scenario: Scenario, runs: int, rng: random.Random) -> Iterable[dict]:
    base = datetime(2026, 6, 13, 0, 0, 0, tzinfo=timezone.utc)
    for run in range(1, runs + 1):
        for seq_idx in range(scenario.sequences):
            seq_start = base + timedelta(minutes=seq_idx + run * 1000)
            for i in range(scenario.events_per_sequence):
                ts = seq_start + timedelta(seconds=i * rng.randint(1, 5))
                if rng.random() < scenario.noisy_ratio:
                    yield _make_noisy_event(rng, scenario, ts, run)
                else:
                    actor = rng.choice(scenario.agents)
                    others = [a for a in scenario.agents if a != actor]
                    target = rng.choice(others) if others and rng.random() < 0.6 else None
                    yield _make_action_event(rng, scenario, ts, run, actor, target)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenarios", default="all",
                   help="Comma-separated scenarios to emit (single,two,three) or 'all'.")
    p.add_argument("--runs", type=int, default=3, help="Independent runs per scenario.")
    p.add_argument("--per-scenario", type=int, default=60,
                   help="Interaction-event sequences per scenario per run.")
    p.add_argument("--noise-ratio", type=float, default=DEFAULT_NOISE_RATIO,
                   help="Share of heartbeat/introspective events in every scenario (default: 0.25).")
    p.add_argument("--seed", type=int, default=20260613, help="RNG seed for determinism.")
    p.add_argument("--out", type=Path, default=None, help="Output .jsonl path (default: stdout).")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    selected = SCENARIOS if args.scenarios == "all" else tuple(s.strip() for s in args.scenarios.split(","))
    unknown = [s for s in selected if s not in SCENARIOS]
    if unknown:
        print(f"Unknown scenario(s): {unknown}", file=sys.stderr)
        return 2
    if not 0.0 <= args.noise_ratio <= 1.0:
        print("--noise-ratio must be between 0.0 and 1.0", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    scenarios = [s for s in build_scenarios(args.per_scenario, args.noise_ratio) if s.name in selected]

    sink = args.out.open("w") if args.out else sys.stdout
    try:
        count = 0
        for sc in scenarios:
            for ev in generate_scenario(sc, args.runs, rng):
                sink.write(json.dumps(ev) + "\n")
                count += 1
        msg = f"Wrote {count} events across {len(scenarios)} scenario(s)."
        print(msg, file=sys.stderr if args.out else sys.stdout)
    finally:
        if args.out:
            sink.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
