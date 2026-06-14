#!/usr/bin/env bash
# Polls the local CPL stack until Kafka, MongoDB, and n8n respond, then prints
# the URLs the operator needs. Exits non-zero after ~2 minutes if anything is
# still unreachable.
set -euo pipefail

deadline=$(( $(date +%s) + 120 ))

check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "✓ ${label}"
    return 0
  fi
  echo "… ${label} not ready"
  return 1
}

echo "Waiting for the CPL stack (timeout: 120s) ..."
while [ "$(date +%s)" -lt "$deadline" ]; do
  ok=true
  check "Kafka broker (localhost:9092)" \
    docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list \
    || ok=false
  check "MongoDB (localhost:27017)" \
    docker compose exec -T mongo mongosh --quiet --eval "db.adminCommand('ping').ok" \
    || ok=false
  check "n8n UI (http://localhost:${N8N_PORT:-5678})" \
    curl -fsS "http://localhost:${N8N_PORT:-5678}/healthz" \
    || ok=false
  if $ok; then
    echo
    echo "READY"
    echo "  n8n UI       : http://localhost:${N8N_PORT:-5678}"
    echo "  Kafka broker : localhost:${KAFKA_HOST_PORT:-9092}"
    echo "  MongoDB      : mongodb://localhost:${MONGO_HOST_PORT:-27017}"
    exit 0
  fi
  sleep 5
done

echo "Timed out waiting for the stack to become ready. Inspect logs with:"
echo "  docker compose logs --tail=80"
exit 1
