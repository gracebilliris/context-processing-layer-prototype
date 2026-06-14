# Pipeline architecture (extended notes)

This document expands on the four-stage pipeline shown in Figure 1 of the
paper and the way it maps to the n8n workflow in `cpl-prototype.json`.

## Stages

### (a) Evidence assignment at ingestion

Every event received from Kafka is assigned a stable `evidence_id` (an
opaque short identifier like `evt:9c2b`) and written **first** to the
append-only `telemetry_raw` collection. This guarantees that, regardless of
what happens downstream, the raw payload is addressable and recoverable.

In the n8n workflow, this is the *Kafka Trigger → Insert raw to MongoDB*
edge. The `evidence_id` is generated either by the producer (preferred,
see `data/generate_synthetic_telemetry.py`) or by a fallback expression
in the trigger.

### (b) Schema-constrained semantic extraction

The *Telemetry Collector Agent* node prompts an LLM (Google Gemini in this
prototype) with the ontology's five classes and required attributes, and
asks the model to emit JSON conforming to the schema. The prompt template
is embedded in the agent node's `systemMessage` (see
`cpl-prototype.json`).

This stage exists because upstream agent telemetry is heterogeneous and
not under our control — we deliberately do **not** require producers to
adopt a shared schema (*schema-on-read*).

### (c) Ontology alignment and conformance validation

Extracted assertions are validated against the ontology
(`ontology/cpl-ontology.ttl`). Assertions that are missing required
attributes, reference undefined classes, or omit `prov:wasDerivedFrom`
are rejected and retained as audit outcomes (with `parseError: true`) in
`telemetry_raw`.

This stage is what allows the knowledge graph to remain queryable under
a stable governance schema even as upstream telemetry drifts over time.

### (d) Provenance-annotated graph insertion

Surviving assertions are inserted into `enriched_telemetry_raw` with
their `prov_wasDerivedFrom` field set to the `evidence_id` from stage
(a). This is the link queried by every governance traversal in
`queries/`.

## Why two collections rather than one?

Separating immutable evidence retention from semantic materialisation is
the central architectural commitment. It makes three things possible:

1. **Re-materialisation** — if the ontology changes, re-run stages (b)–(d)
   over the unchanged `telemetry_raw` to regenerate the knowledge graph.
2. **Audit reproducibility** — every assertion's justification is one
   `$lookup` away.
3. **Drift isolation** — stage (c) is the only component that needs to
   change when upstream payload formats shift.

## Why MongoDB for both stores?

Pragmatism for the prototype: a single dependency, document-shaped raw
events fit naturally, and the `$lookup` operator gives us cheap
provenance-traversal joins. A production deployment could swap the
knowledge graph for a triple store (e.g., GraphDB, Fuseki) without
changing stages (a)–(c).
