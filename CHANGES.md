# Artifact fixes

- `artifact-telemetry-raw-write`: added raw evidence preparation and `telemetry_raw` insertion before enrichment, including UUID v4 `evidence_id`, original payload, ingest timestamp, and Kafka metadata.
- `artifact-prov-wasderivedfrom`: materialised assertions now carry top-level `prov:wasDerivedFrom` URNs while retaining `attributes.evidence_id`.
- `artifact-graphdb-alignment`: added Apache Jena Fuseki (`/cpl`) to Compose and pointed SPARQL updates at `http://fuseki:3030/cpl/update`.
- `artifact-static-ontology-contract`: replaced runtime ontology generation with a static ontology contract derived from `ontology/cpl-ontology.ttl`.
- `artifact-shacl-validation`: added `ontology/cpl-shapes.ttl` and workflow validation that writes violations to `failed_assertions`.
- `artifact-strict-parse-errors`: JSON parse and missing timestamp failures now produce explicit failed records without defaulting to `{}`, `now()`, or confidence `1.0`.
