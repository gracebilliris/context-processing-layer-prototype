# Synthetic telemetry corpus

`generate_synthetic_telemetry.py` recreates the 60-event-per-scenario corpus
used in the paper's feasibility evaluation. The corpus simulates a college
application workflow over three multi-agent scenarios:

| Scenario | Agents involved                                         | Notes |
| -------- | ------------------------------------------------------- | ----- |
| `single` | One retrieval agent only                                | Many introspective / heartbeat events (lower semantic-success rate). |
| `two`    | Retrieval + financial-eligibility agents                | Cross-references between agents appear in payloads. |
| `three`  | Retrieval + financial + external-portal agents          | Richest cross-references; highest semantic-success rate. |

Source records: the publicly available Kaggle dataset *International Students
Applying to U.S. Colleges*. Only **derived event sequences** are emitted to
this repository (no upstream PII is republished).

## Usage

```bash
python -m pip install -r data/requirements.txt
python data/generate_synthetic_telemetry.py \
    --scenarios all \
    --runs 3 \
    --seed 20260613 \
    --out data/events.jsonl
```

Each line of the output `.jsonl` is a single interaction event ready for the
Kafka publisher (`scripts/publish_to_kafka.py`). Events deliberately vary in
shape (key–value pairs, nested objects, free-text annotations) to simulate
heterogeneous agent telemetry.

## Reproducibility

- Passing the same `--seed` yields a byte-identical corpus.
- No network calls are made; the generator runs offline.
- Source code: ~200 lines of plain Python; no ML models are loaded.
