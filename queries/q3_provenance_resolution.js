// q3: Semantic-success metric (paper Table 2, last column).
// For every assertion in the knowledge graph, check whether its
// prov:wasDerivedFrom link resolves to an event in the context store.
// Reports the success percentage per scenario.

const db = db.getSiblingDB("cpl");

const results = db.enriched_telemetry_raw.aggregate([
  { $match: { parseError: { $ne: true } } },
  { $lookup: {
      from: "telemetry_raw",
      localField: "prov_wasDerivedFrom",
      foreignField: "evidence_id",
      as: "evidence"
  } },
  { $addFields: {
      resolved: { $gt: [ { $size: "$evidence" }, 0 ] },
      scenario: { $ifNull: [ "$raw.scenario", { $ifNull: [ "$scenario", "unknown" ] } ] }
  } },
  { $group: {
      _id: "$scenario",
      total: { $sum: 1 },
      resolved: { $sum: { $cond: [ "$resolved", 1, 0 ] } }
  } },
  { $project: {
      _id: 0,
      scenario: "$_id",
      total: 1,
      resolved: 1,
      semantic_success_pct: { $multiply: [ { $divide: [ "$resolved", "$total" ] }, 100 ] }
  } },
  { $sort: { scenario: 1 } }
]).toArray();

print("Provenance resolution rate per scenario:");
printjson(results);
