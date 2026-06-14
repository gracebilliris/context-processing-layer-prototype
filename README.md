# CPL: Context Processing Layer Prototype

> A prototype tool that brings **semantic observability** to multi-agent AI
> systems by retaining raw telemetry as immutable evidence and materialising
> ontology-conformant, provenance-linked assertions in a knowledge graph.

This repository accompanies the paper *"CPL: A Context Processing Layer Tool
for Semantic Observability in Multi-Agent AI Systems"* (Billiris et al.). It
contains everything needed to reproduce the feasibility evaluation reported in
the paper on a single laptop.

📺 **Demo video:** <https://youtu.be/G9Vybd47vMw>

---

## Table of contents

1. [What this prototype does](#what-this-prototype-does)
2. [Architecture at a glance](#architecture-at-a-glance)
3. [Repository layout](#repository-layout)
4. [Quickstart (≈10 minutes)](#quickstart-10-minutes)
5. [Reproducing the paper evaluation](#reproducing-the-paper-evaluation)
6. [Sample governance queries](#sample-governance-queries)
7. [Configuration reference](#configuration-reference)
8. [Troubleshooting](#troubleshooting)
9. [Citing this work](#citing-this-work)
10. [License](#license)

---

## What this prototype does

Multi-agent AI systems emit large volumes of telemetry — tool invocations,
delegations, intermediate artefacts — but conventional observability pipelines
discard the raw payloads after deriving metrics and spans. Once discarded, no
later query can reconstruct the chain from a derived assertion back to its
originating event, so **governance questions become unanswerable**:

> *Which agent accessed the student's profile, through which tool, and based
> on what evidence?*

CPL addresses this with two design principles:

1. **Immutable evidence retention** — every raw interaction event is stored,
   addressable, and append-only in a context store.
2. **Provenance-linked materialisation** — each assertion written to the
   knowledge graph carries an explicit `prov:wasDerivedFrom` pointer to the
   evidence event(s) it was derived from.

The result is a knowledge graph you can query semantically *and* trace back to
the raw bytes that justify every claim.

## Architecture at a glance

```
 ┌────────────┐     ┌─────────┐     ┌──────────────────────────────────┐
 │ Agents /   │ ──▶ │  Kafka  │ ──▶ │  CPL n8n pipeline                │
 │ Tools /    │     │ broker  │     │  (a) evidence assignment          │
 │ APIs       │     └─────────┘     │  (b) schema-constrained extract   │
 └────────────┘                     │  (c) ontology conformance check   │
                                    │  (d) provenance-annotated insert  │
                                    └────────┬───────────────┬─────────┘
                                             ▼               ▼
                                   ┌──────────────┐  ┌────────────────┐
                                   │ Context      │  │ Knowledge      │
                                   │ store        │  │ graph          │
                                   │ (MongoDB,    │  │ (MongoDB,      │
                                   │  append-only)│  │  triple-like)  │
                                   └──────────────┘  └────────────────┘
```

In this prototype both stores are MongoDB collections inside the same
instance:

| Logical role     | MongoDB collection         | Notes                                   |
| ---------------- | -------------------------- | --------------------------------------- |
| Context store    | `telemetry_raw`            | Append-only; every event keyed by `evidence_id` |
| Knowledge graph  | `enriched_telemetry_raw`   | Conformant assertions with `prov_wasDerivedFrom` |

The n8n workflow (`cpl-prototype.json`) implements the four pipeline stages
using a Kafka trigger, a Google Gemini-backed LangChain agent, and two
MongoDB nodes.

## Repository layout

```
.
├── README.md                  ← you are here
├── REPLICATION.md             ← step-by-step paper reproduction guide
├── LICENSE
├── docker-compose.yml         ← Kafka + Zookeeper + MongoDB + n8n
├── .env.example               ← environment variables (copy to .env)
├── cpl-prototype.json         ← n8n workflow export (the pipeline)
├── ontology/
│   └── cpl-ontology.ttl       ← Turtle file of the 5-class CPL ontology
├── data/
│   ├── generate_synthetic_telemetry.py   ← reproduces the 60-event corpus
│   └── README.md
├── queries/
│   ├── q1_who_accessed_pii.js            ← MongoDB shell governance queries
│   ├── q2_tool_chain_for_action.js
│   ├── q3_provenance_resolution.js
│   └── README.md
├── scripts/
│   ├── publish_to_kafka.py     ← replay events into the CPL pipeline
│   ├── healthcheck.sh          ← verify the stack is up
│   └── seed_n8n_credentials.md ← one-time n8n credential setup
└── docs/
    └── architecture.md         ← extended notes on the pipeline stages
```

## Quickstart (≈10 minutes)

### Prerequisites

| Tool            | Tested version | Why                                  |
| --------------- | -------------- | ------------------------------------ |
| Docker          | ≥ 24.0         | Runs the full stack via Compose      |
| Docker Compose  | v2 plugin      | `docker compose ...`                 |
| Python          | ≥ 3.10         | Synthetic telemetry generator + publisher |
| `pip`           | recent         | Installing `kafka-python`, `faker`   |
| A Google Gemini API key | n/a    | The n8n agent calls Gemini for extraction |

> **No Gemini key?** You can still bring the stack up and inspect the
> pipeline, but the extraction stage will fail. See
> [Troubleshooting](#troubleshooting) for how to swap in a local model.

### 1. Clone and configure

```bash
git clone https://github.com/gracebilliris/context-processing-layer-prototype.git
cd context-processing-layer-prototype
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=...
```

### 2. Start the stack

```bash
docker compose up -d
./scripts/healthcheck.sh
```

The healthcheck waits for Kafka, MongoDB, and n8n to be reachable and prints
URLs. Expect the first start to take ~60s while images are pulled.

### 3. Import the n8n workflow and credentials

1. Open <http://localhost:5678> and create the local n8n owner account.
2. Go to **Workflows → Import from File** and select `cpl-prototype.json`.
3. Create the three credentials referenced by the workflow:
   - **Kafka** → broker `kafka:9092` (the in-network hostname).
   - **MongoDB** → connection string `mongodb://cpl:cpl@mongo:27017/cpl?authSource=admin`.
   - **Google Gemini (PaLM) API** → paste your API key.
4. Open the imported workflow and click **Activate** (top right).

Detailed screenshots and field-by-field instructions are in
[`scripts/seed_n8n_credentials.md`](scripts/seed_n8n_credentials.md).

### 4. Generate and publish synthetic telemetry

```bash
python -m pip install -r data/requirements.txt
python data/generate_synthetic_telemetry.py --scenarios all --out data/events.jsonl
python scripts/publish_to_kafka.py --input data/events.jsonl --topic context-processing-layer-trigger-topic
```

You should see the n8n workflow execute once per event and writes appearing
in MongoDB.

### 5. Inspect the result

```bash
docker compose exec mongo mongosh -u cpl -p cpl --authenticationDatabase admin cpl \
  --eval 'db.enriched_telemetry_raw.countDocuments()'
```

Then try the [sample governance queries](#sample-governance-queries) below.

## Reproducing the paper evaluation

The full step-by-step procedure that regenerates the numbers in Table 2 of
the paper (throughput, latency, semantic-success rate across single-, two-,
and three-agent scenarios) is in [REPLICATION.md](REPLICATION.md). The
short version:

```bash
# clean state
docker compose down -v && docker compose up -d && ./scripts/healthcheck.sh
# regenerate the 60-event corpus
python data/generate_synthetic_telemetry.py --scenarios all --runs 3 --out data/events.jsonl
# replay with timing instrumentation
python scripts/publish_to_kafka.py --input data/events.jsonl --measure --report report.json
# verify provenance resolution rate
mongosh ... < queries/q3_provenance_resolution.js
```

`report.json` contains throughput and end-to-end latency per scenario;
`q3_provenance_resolution.js` reports the semantic-success percentage.

## Sample governance queries

All three queries from the paper's running example are in [`queries/`](queries/)
and runnable against the MongoDB knowledge graph:

| File | Question it answers |
| ---- | ------------------- |
| `q1_who_accessed_pii.js` | *Which agents accessed the student profile?* |
| `q2_tool_chain_for_action.js` | *Which tool invocation transmitted the data externally, and via which delegation chain?* |
| `q3_provenance_resolution.js` | *For every assertion, does the `prov_wasDerivedFrom` link resolve to a retained event?* (semantic-success metric) |

Run any of them with:

```bash
docker compose exec mongo mongosh -u cpl -p cpl --authenticationDatabase admin cpl \
  < queries/q1_who_accessed_pii.js
```

## Configuration reference

All runtime configuration is in `.env` (copied from `.env.example`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `GEMINI_API_KEY` | *(unset)* | Required for the extraction stage |
| `KAFKA_TOPIC` | `context-processing-layer-trigger-topic` | Topic CPL listens on |
| `MONGO_INITDB_ROOT_USERNAME` | `cpl` | MongoDB root user |
| `MONGO_INITDB_ROOT_PASSWORD` | `cpl` | MongoDB root password (change for non-local use) |
| `N8N_PORT` | `5678` | Host port for the n8n UI |
| `N8N_BASIC_AUTH_USER` | `admin` | Optional basic auth for n8n |
| `N8N_BASIC_AUTH_PASSWORD` | `changeme` | Optional basic auth for n8n |

## Troubleshooting

**`Kafka Trigger` shows no executions.**
Confirm the topic exists and the workflow is active:

```bash
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
```

If empty, the publisher will auto-create the topic on first publish, but the
n8n trigger needs to be (re)activated after the topic appears.

**`MongooseServerSelectionError` / cannot reach MongoDB.**
Inside n8n, the host must be `mongo` (the Compose service name), not
`localhost`. From your laptop shell, use `localhost:27017`.

**Gemini quota or auth errors.**
Either rotate the key in `.env` and `docker compose restart n8n`, or swap to
a local extractor: replace the *Google Gemini Chat Telemetry Model* node
with an *Ollama Chat Model* node pointed at a model that supports JSON-mode
output (e.g. `llama3.1:8b-instruct`). The downstream conformance check is
unchanged.

**`parseError: true` on most events.**
The extractor could not satisfy the ontology schema. Check the raw event
shape in `telemetry_raw` — if events are very short status pings without
agent/tool fields, this is expected and is exactly the failure mode
discussed in the paper's *Discussion* section.

**Ports already in use.**
Edit `.env` to remap any of `N8N_PORT`, `KAFKA_HOST_PORT`, `MONGO_HOST_PORT`
and rerun `docker compose up -d`.

## Citing this work

If you use CPL in academic work, please cite:

```bibtex
@inproceedings{billiris2026cpl,
  title     = {CPL: A Context Processing Layer Tool for Semantic Observability
               in Multi-Agent AI Systems},
  author    = {Billiris, Grace and Gill, Asif and Haggag, Omar and
               Bandara, Madhushi and Grundy, John},
  booktitle = {Proceedings of the CBI-EDOC 2026 Tools \& Demos Track},
  year      = {2026}
}
```

## License

See [LICENSE](LICENSE).
