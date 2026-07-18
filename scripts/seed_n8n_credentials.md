# One-time n8n credential setup

After `docker compose up -d` and importing `cpl-prototype.json` via
**Workflows → Import from File**, create the three credentials below. The
credential **names** must match exactly — they are referenced by name in the
imported workflow.

## 1. Kafka

| Field          | Value                       |
| -------------- | --------------------------- |
| Credential name| `Local`                     |
| Bootstrap servers | `kafka:29092`            |
| SSL            | off                         |
| Authentication | none                        |

> Use `kafka:29092` when connecting from within the docker network (e.g. n8n
> container); use `localhost:9092` from the host.

## 2. MongoDB

| Field          | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| Credential name| `telemetry_db mongodb`                                             |
| Configuration  | Connection String                                                  |
| Connection     | `mongodb://cpl:cpl@mongo:27017/cpl?authSource=admin`               |
| Database       | `cpl`                                                              |

> The hostname must be `mongo` (Docker network alias) — *not* `localhost`,
> which would resolve inside the n8n container.

## 3. Google Gemini (PaLM) API

| Field          | Value                                |
| -------------- | ------------------------------------ |
| Credential name| `Google Gemini(PaLM) Api Telemetry`  |
| API Key        | *(paste from `.env` `GEMINI_API_KEY`)* |

## Verifying

After saving all three, open the imported workflow and click **Execute
Workflow** once. The Kafka Trigger will not fire (no event yet), but each
configured node should show a green credential indicator. If any shows red,
re-open it and re-select the credential by name.

Finally, click **Activate** in the top right. The workflow will then process
events as soon as you run `scripts/publish_to_kafka.py`.
