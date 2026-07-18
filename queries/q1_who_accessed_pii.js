// q1: Which agents accessed the student profile?
// Walks the knowledge graph collection for any :AgentAction whose
// :accessedData references the student_profile entity, then projects the
// performing agent and the originating evidence id.

const db = db.getSiblingDB("cpl");

print("Agents that accessed the student profile (with provenance):");
printjson(
  db.enriched_telemetry_raw.aggregate([
    { $match: { accessed_data: "student_profile", parseError: { $ne: true } } },
    { $project: {
        _id: 0,
        agent: "$actor",
        tool: "$tool",
        ts: "$timestamp",
        evidence_id: "$evidence_id",
        "prov:wasDerivedFrom": "$prov:wasDerivedFrom"
    } },
    { $sort: { ts: 1 } }
  ]).toArray()
);
