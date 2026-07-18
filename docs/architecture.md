# Pipeline architecture (extended notes)

This document expands on the four-stage pipeline shown in Figure 1 of the
paper and the way it maps to the n8n workflow in `cpl-prototype.json`.

## Stages

### (a) Evidence assignment at ingestion

Every event received from Kafka is assigned a stable UUID v4 `evidence_id`
and written **first** to the append-only `telemetry_raw` collection with the
original `raw_payload`, `ingest_timestamp`, `kafka_topic`, `kafka_partition`,
and `kafka_offset`. This guarantees that, regardless of what happens
downstream, the raw payload is addressable and recoverable.

In the n8n workflow, this is the *Kafka Trigger → Prepare Raw Evidence →
Insert Raw Evidence to MongoDB* edge. Downstream nodes reuse the same
`evidence_id` and represent the provenance target as
`urn:cpl:evidence:<evidence_id>`.

### (b) Schema-constrained semantic extraction

The *Attach Static Ontology Contract* helper inlines the runtime summary of
`ontology/cpl-ontology.ttl` into the *Telemetry Collector Agent* prompt. The
LLM (Google Gemini in this prototype) is instructed to map into exactly the
published classes/properties and must not create an ontology or mapping per
event.

This stage exists because upstream agent telemetry is heterogeneous and
not under our control — we deliberately do **not** require producers to
adopt a shared schema (*schema-on-read*).

### (c) Ontology alignment and conformance validation

Extracted assertions are validated against the closed-world SHACL contract
(`ontology/cpl-shapes.ttl`). The workflow implements this with the
*Validate Assertion with SHACL Contract* node, which checks the same required
properties before storage. Assertions that fail strict JSON parsing, omit a
timestamp, omit `prov:wasDerivedFrom`, or miss class-required fields are
written to `failed_assertions` with a `shaclReport`; they are not silently
normalised or inserted into the materialised graph.

This stage is what allows the knowledge graph to remain queryable under
a stable governance schema even as upstream telemetry drifts over time.

### (d) Provenance-annotated graph insertion

Surviving assertions are inserted into `enriched_telemetry_raw` with a
top-level `prov:wasDerivedFrom` field set to
`urn:cpl:evidence:<evidence_id>`. `attributes.evidence_id` is retained for
backward compatibility. The same assertion is compiled into RDF and posted
to Apache Jena Fuseki at `http://fuseki:3030/cpl/update`; SPARQL queries can
target `http://fuseki:3030/cpl/query`.

## Why MongoDB plus Fuseki?

Separating immutable evidence retention, document materialisation, and RDF
assertion storage is the central architectural commitment:

1. **Re-materialisation** — if the ontology changes, re-run stages (b)–(d)
   over the unchanged `telemetry_raw` to regenerate MongoDB documents and
   Fuseki triples.
2. **Audit reproducibility** — every assertion's justification is one
   `$lookup` away in MongoDB and one `prov:wasDerivedFrom` traversal away in
   RDF.
3. **Drift isolation** — stage (c) is the only component that needs to
   change when upstream payload formats shift.

MongoDB remains the evidence and operational query store used by the sample
`queries/*.js`; Fuseki is the RDF triple store that aligns the prototype with
the SPARQL deployment described in the paper.
