#!/usr/bin/env bash
# Manage the local OTel + Jaeger + ClickHouse stack.
#
# Usage:
#   ./infra/stack.sh up        # start all containers, wait for health
#   ./infra/stack.sh down      # stop containers (keeps ClickHouse data)
#   ./infra/stack.sh wipe      # stop AND delete ClickHouse volume
#   ./infra/stack.sh status    # show container state
#   ./infra/stack.sh logs [svc] # tail logs (all services, or one)

set -euo pipefail
cd "$(dirname "$0")"

DC="sudo docker compose"

case "${1:-up}" in
  up)
    $DC up -d --wait
    echo
    echo "Stack ready:"
    echo "  OTLP gRPC        :4317         <- workflow.py sends here"
    echo "  Grafana UI       http://localhost:3000          (Explore -> Tempo for trace waterfalls)"
    echo "  Tempo API        http://localhost:3200          (direct query if needed)"
    echo "  ClickHouse HTTP  http://localhost:8123          (try /play for SQL UI)"
    echo "  ClickHouse data  docker volume: infra_ch-data"
    echo "  Tempo data       docker volume: infra_tempo-data"
    ;;
  down)
    $DC down
    ;;
  wipe)
    echo "This deletes ALL persisted trace data. Type 'yes' to confirm:"
    read -r confirm
    if [ "$confirm" = "yes" ]; then
      $DC down -v
    else
      echo "Aborted."
    fi
    ;;
  status)
    $DC ps
    ;;
  logs)
    $DC logs -f "${2:-}"
    ;;
  *)
    echo "Usage: $0 {up|down|wipe|status|logs [service]}" >&2
    exit 1
    ;;
esac
