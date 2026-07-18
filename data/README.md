# Synthetic telemetry corpus

`generate_synthetic_telemetry.py` recreates the 60-sequence-per-scenario corpus
used in the paper's feasibility evaluation. The corpus simulates a college
application workflow over three multi-agent scenarios:

| Scenario | Agents involved                                | Events per sequence | Notes |
| -------- | ---------------------------------------------- | ------------------- | ----- |
| `single` | One retrieval agent only                       | 4                   | Baseline single-agent trace. |
| `two`    | Retrieval + financial-eligibility agents       | 6                   | Cross-references between agents appear in payloads. |
| `three`  | Retrieval + financial + external-portal agents | 8                   | Richest cross-references. |

Source records: the publicly available Kaggle dataset *International Students
Applying to U.S. Colleges*. Only **derived event sequences** are emitted to
this repository (no upstream PII is republished).

## Usage

```bash
python -m pip install -r data/requirements.txt
python data/generate_synthetic_telemetry.py \
    --scenarios all \
    --runs 3 \
    --noise-ratio 0.25 \
    --seed 20260613 \
    --out data/events.jsonl
```

Each line of the output `.jsonl` is a single interaction event ready for the
Kafka publisher (`scripts/publish_to_kafka.py`). Events deliberately vary in
shape (key–value pairs, nested objects, free-text annotations) to simulate
heterogeneous agent telemetry.

With the defaults, the generator emits 3,240 events total: 720 `single`, 1,080
`two`, and 1,440 `three`. The `--noise-ratio` flag controls the share of
heartbeat/introspective events and defaults to `0.25` for every scenario. This
constant noise ratio avoids confounding workload cleanliness with agent count
when comparing semantic-success rates across one-, two-, and three-agent
scenarios.

## Reproducibility

- Passing the same `--seed` yields a byte-identical corpus.
- Passing the same `--noise-ratio` applies that ratio uniformly across all
  selected scenarios.
- No network calls are made; the generator runs offline.
- Source code: ~200 lines of plain Python; no ML models are loaded.
