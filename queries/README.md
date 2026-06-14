# Sample governance queries

Three runnable `mongosh` scripts that demonstrate CPL's core promise:
*every assertion in the knowledge graph can be traced back to the raw event
that justified it.*

| Script                          | Governance question                                                              |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `q1_who_accessed_pii.js`        | Which agents accessed the student profile, and via which tool?                   |
| `q2_tool_chain_for_action.js`   | For each access, what was the tool chain *and* the originating raw payload?       |
| `q3_provenance_resolution.js`   | What fraction of assertions resolve to a retained evidence event? (the semantic-success metric in Table 2) |

## Running

With the stack up (see [`../README.md`](../README.md)):

```bash
docker compose exec mongo mongosh \
    -u cpl -p cpl --authenticationDatabase admin cpl \
    < queries/q1_who_accessed_pii.js
```

Each script is plain JavaScript, ~20–40 lines, and is intentionally
self-contained so it can be adapted to other governance questions without
touching the pipeline.
