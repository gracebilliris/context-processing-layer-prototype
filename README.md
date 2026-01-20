# Context Processing Layer Prototype

This demonstration showcases a telemetry processing workflow built with n8n, an open-source workflow automation platform. It illustrates how normalised telemetry data can be ingested, enriched with contextual metadata, and stored for further analysis with minimal coding.

## Overview

The workflow is designed as a Context Processing Layer in an observability architecture for agentic AI systems. It processes incoming telemetry events from a Kafka topic, uses AI to extract and enrich contextual information, and stores the enriched data in MongoDB.

### Key Components:

1. **Ingestion Workflow**
   - **Input:** Normalised telemetry events from Kafka topic `context-processing-layer-trigger-topic`.
   - **Process:**
     - Events are consumed via Kafka Trigger node.
     - Telemetry Collector Agent (powered by Google Gemini AI) transforms the data into enriched contextual metadata.
     - Enriched events are inserted into the `enriched_telemetry_raw` MongoDB collection.

2. **Data Enrichment Process**
   - **AI Agent Role:** The Telemetry Collector Agent extracts key entities (agents, tasks, humans, models, systems), identifies attributes and relationships, computes contextual values like duration and severity.
   - **Output Structure:** JSON with fields like timestamp, actor, target, job, severity, duration_ms, relationships, attributes, context_summary, confidence, and raw data.
   - **Error Handling:** Sets parseError flag if critical data is missing.

## Purpose

This prototype demonstrates the feasibility of a Context Processing Layer in a Federated Observability Architecture Pattern for reliable agentic AI software systems. It shows how telemetry can be processed, enriched with AI-driven context, and prepared for monitoring and analysis in a traceable, automated workflow.

## Note

This is a feasibility prototype built with n8n workflows. It assumes input telemetry is already normalised and focuses on contextual enrichment using AI.

## Files

- `cpl-prototype.json`: n8n workflow export file containing the complete workflow configuration.
- `LICENSE`: Project license information.

## Requirements

- n8n instance
- Kafka broker
- MongoDB database
- Google Gemini API credentials

## Setup

1. Import `cpl-prototype.json` into your n8n instance.
2. Configure the required credentials (Kafka, MongoDB, Google Gemini API).
3. Ensure the Kafka topic and MongoDB collections exist.
4. Activate the workflow.

For more details on n8n workflows, visit [n8n.io](https://n8n.io).