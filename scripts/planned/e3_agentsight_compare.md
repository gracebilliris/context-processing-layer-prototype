# E3 (planned): Head-to-head comparison with AgentSight

This document records the protocol we will follow for the planned
comparison between CPL and AgentSight [Zheng et al., 2025] on an
identical multi-agent workload.

## Workload

The 540-event corpus produced by:

```bash
python data/generate_synthetic_telemetry.py --scenarios all --runs 3 --out data/events.jsonl
```

is replayed through both systems back-to-back with cleared state between
runs.

## Metrics (matching Table 1 of the paper)

| Dimension              | Operationalisation                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| Evidence retention     | Fraction of events whose raw payload remains independently addressable post-processing.             |
| Semantic conformance   | Fraction of derived statements that pass an ontology validator.                                     |
| Governance query       | Whether the running-example query (`queries/q1_who_accessed_pii.js`) is answerable by traversal vs. by log re-derivation, and the wall-clock cost of each. |

## Status

Not yet executed. The harness scaffolding lives in
`scripts/publish_to_kafka.py` (CPL side) and will need a thin adapter on
the AgentSight side, which we will add once AgentSight's release is
pinned to a reproducible version.
