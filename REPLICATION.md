# Reproducing the CPL feasibility evaluation

This guide reproduces Table 2 of the paper (throughput, latency, and
semantic-success rate across the three multi-agent scenarios) on a single
laptop. Allow roughly **30 minutes** including the Docker image pulls.

## 0. Hardware and software baseline

- A laptop with ≥ 8 GB RAM and ≥ 10 GB free disk.
- Docker ≥ 24, Docker Compose v2, Python ≥ 3.10.
- A Google Gemini API key (paid tier recommended; the free tier rate-limits
  the three-agent scenario).
- Network access to pull `confluentinc/cp-kafka`, `mongo:7`, `n8nio/n8n`,
  and PyPI packages.

## 1. Clean slate

```bash
docker compose down -v   # wipe any previous Kafka offsets and Mongo data
docker compose up -d
./scripts/healthcheck.sh
```

`healthcheck.sh` polls until Kafka, MongoDB, and n8n respond. Re-run it
until it prints `READY`.

## 2. Import the workflow and credentials

Follow [`scripts/seed_n8n_credentials.md`](scripts/seed_n8n_credentials.md)
exactly. The credential **names** (not just types) must match the names
embedded in `cpl-prototype.json`, otherwise the imported workflow will
reference unresolved credential IDs.

Use `kafka:29092` when connecting from within the docker network (e.g. n8n
container); use `localhost:9092` from the host.

Activate the workflow before publishing any events.

## 3. Regenerate the synthetic corpus

```bash
python -m pip install -r data/requirements.txt
python data/generate_synthetic_telemetry.py \
    --scenarios single,two,three \
    --runs 3 \
    --noise-ratio 0.25 \
    --seed 20260613 \
    --out data/events.jsonl
wc -l data/events.jsonl
```

This produces **3,240 events** in `data/events.jsonl` with the current
defaults: `single` = 60 sequences × 4 events × 3 runs = **720 events**,
`two` = 60 × 6 × 3 = **1,080 events**, and `three` = 60 × 8 × 3 =
**1,440 events**. The exact reproduction command above should therefore print
`3240` from `wc -l`. The `--seed` flag makes the corpus deterministic, and
`--noise-ratio 0.25` applies the same heartbeat/introspective-event ratio to
all three scenarios.

## 4. Replay through the pipeline with instrumentation

```bash
python scripts/publish_to_kafka.py \
    --input data/events.jsonl \
    --topic context-processing-layer-trigger-topic \
    --measure \
    --report report.json
```

`--measure` records per-event ingest timestamps and joins them, after
processing completes, with the `materialised_at` timestamp written by the
final n8n MongoDB node. The script waits until the count in
`enriched_telemetry_raw` plus the count of rejected events equals the
number of events published, with a 15-minute timeout per scenario.

The output `report.json` contains:

```jsonc
{
  "scenarios": {
    "single":  { "events": 720, "processed": 720, "throughput_per_min": 10, "elapsed_wall_clock_s": 4320, "avg_latency_s": 398, "semantic_success_pct": 65.0 },
    "two":     { "events": 1080, "processed": 1080, "throughput_per_min": 15, "elapsed_wall_clock_s": 4320, "avg_latency_s": 798, "semantic_success_pct": 70.7 },
    "three":   { "events": 1440, "processed": 1440, "throughput_per_min": 18, "elapsed_wall_clock_s": 4800, "avg_latency_s": 951, "semantic_success_pct": 82.0 }
  }
}
```

Your numbers will differ slightly depending on Gemini latency on the day,
but the **relative ordering** (semantic success rising with agent count;
latency dominated by extraction) should hold.

## 5. Cross-check semantic success with a graph query

```bash
docker compose exec mongo mongosh \
    -u cpl -p cpl --authenticationDatabase admin cpl \
    < queries/q3_provenance_resolution.js
```

This recomputes the semantic-success percentage by asking the knowledge
graph directly: *what fraction of enriched documents carry a
`prov_wasDerivedFrom` link that resolves to a document in
`telemetry_raw`?* The two numbers (from `report.json` and from this query)
should agree.

## 6. Reproduce the governance-query traversal

```bash
docker compose exec mongo mongosh \
    -u cpl -p cpl --authenticationDatabase admin cpl \
    < queries/q1_who_accessed_pii.js
docker compose exec mongo mongosh \
    -u cpl -p cpl --authenticationDatabase admin cpl \
    < queries/q2_tool_chain_for_action.js
```

`q1` returns the retrieval agent action; `q2` walks
`:AgentAction → :usedTool → prov:wasDerivedFrom → telemetry_raw` and
prints both the tool invocation and the originating raw payload, which is
the traversal illustrated in Figure 3 of the paper.

## 7. Tear down

```bash
docker compose down -v
```

## Notes on planned-but-not-yet-run experiments (E1–E3)

The paper's *Planned Evaluation Extensions* subsection scopes three
follow-up experiments. Stubs for each live in
[`scripts/planned/`](scripts/planned/) and are intentionally **not**
required to reproduce the feasibility numbers above:

- `e1_scalability.py` — load generator that sweeps ingest rate from
  `10^2` to `10^4` events/min.
- `e2_noisy_corpora.py` — corpus extender with malformed / out-of-order
  / duplicate event injection.
- `e3_agentsight_compare.md` — protocol for the head-to-head replay
  against AgentSight on the same workload.

Contributions and pull requests against these scripts are welcome.

## Recent revisions addressing reviewer feedback

- `eval-noise-ratio-constant`: `data/generate_synthetic_telemetry.py` now uses
  a constant 25% noise ratio for all scenarios, configurable with
  `--noise-ratio`.
- `eval-event-count-fix`: this guide now documents the generator's actual
  default output of 3,240 events, including per-scenario counts and the exact
  reproduction command.
- `repro-add-pymongo-requirement`: `data/requirements.txt` now includes
  `pymongo>=4.0` for measurement-mode MongoDB reads.
- `repro-kafka-port-docs`: n8n-in-docker instructions now use `kafka:29092`;
  host-side commands continue to use `localhost:9092`.
- `repro-measurement-timeout`: `scripts/publish_to_kafka.py` now applies
  per-scenario timeouts and computes throughput from processed events divided
  by elapsed wall-clock time, keeping latency separate.
