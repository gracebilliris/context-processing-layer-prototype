# Governance query trace

Given a synthetic event where an agent uses a tool to access `student_profile`:

1. `Prepare Raw Evidence` assigns `evidence_id`, then `Insert Raw Evidence to MongoDB` stores the original event in `telemetry_raw`.
2. The extractor emits `tool`, `accessed_data: "student_profile"`, `attributes.evidence_id`, and `prov:wasDerivedFrom: "urn:cpl:evidence:<evidence_id>"`.
3. The SHACL validation node requires timestamp, actor, tool, accessed data, evidence fields, and `prov:wasDerivedFrom`; valid records enter `enriched_telemetry_raw`.
4. `q1_who_accessed_pii.js` matches `accessed_data: "student_profile"` and projects the agent/tool/provenance fields.
5. `q2_tool_chain_for_action.js` strips the URN prefix and joins to `telemetry_raw.evidence_id`, returning the raw evidence payload.
6. `q3_provenance_resolution.js` performs the same provenance join for every non-parse-error assertion, so valid synthetic events resolve as semantic successes.
