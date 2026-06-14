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

Activate the workflow before publishing any events.

## 3. Regenerate the synthetic corpus

```bash
python -m pip install -r data/requirements.txt
python data/generate_synthetic_telemetry.py \
    --scenarios single,two,three \
    --runs 3 \
    --seed 20260613 \
    --out data/events.jsonl
```

This produces 60 events per scenario × 3 scenarios × 3 runs = **540 events**
in `data/events.jsonl`. The `--seed` flag makes the corpus deterministic.
The paper's headline numbers are reported per scenario, averaged across the
three runs.

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
    "single":  { "events": 180, "throughput_per_min": 10, "avg_latency_s": 398, "semantic_success_pct": 65.0 },
    "two":     { "events": 180, "throughput_per_min": 15, "avg_latency_s": 798, "semantic_success_pct": 70.7 },
    "three":   { "events": 180, "throughput_per_min": 18, "avg_latency_s": 951, "semantic_success_pct": 82.0 }
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
