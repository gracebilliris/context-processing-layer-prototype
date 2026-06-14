// q2: For each agent action against the student profile, reconstruct the
// tool-invocation chain AND the raw evidence payload by joining the
// knowledge graph (enriched_telemetry_raw) back to the immutable context
// store (telemetry_raw) via the prov:wasDerivedFrom link.

const db = db.getSiblingDB("cpl");

print("Tool chain and raw evidence for student_profile accesses:");
printjson(
  db.enriched_telemetry_raw.aggregate([
    { $match: { accessed_data: "student_profile", parseError: { $ne: true } } },
    { $lookup: {
        from: "telemetry_raw",
        localField: "prov_wasDerivedFrom",
        foreignField: "evidence_id",
        as: "evidence"
    } },
    { $project: {
        _id: 0,
        agent: "$actor",
        tool: "$tool",
        delegated_to: "$target_agent",
        ts: "$timestamp",
        evidence_id: "$evidence_id",
        prov_wasDerivedFrom: "$prov_wasDerivedFrom",
        evidence_resolved: { $gt: [ { $size: "$evidence" }, 0 ] },
        evidence_payload: { $arrayElemAt: [ "$evidence", 0 ] }
    } },
    { $sort: { ts: 1 } }
  ]).toArray()
);
