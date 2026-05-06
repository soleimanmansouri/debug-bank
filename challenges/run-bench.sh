#!/usr/bin/env bash
# Debug-Bench runner
#
# Usage:
#   ./run-bench.sh S01              # start S01 environment
#   ./run-bench.sh S02              # start S02 environment
#   ./run-bench.sh S03              # start S03 environment
#   ./run-bench.sh S01 --down       # tear down S01 environment
#   ./run-bench.sh --score S01 trajectory.json   # score a trajectory file
#
# After starting, the agent investigates the running environment.
# When done, run with --down to clean up, then score with --score.

set -euo pipefail

CHALLENGES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

declare -A SCENARIO_DIRS=(
  [S01]="S01-stale-cache-race"
  [S02]="S02-retry-storm"
  [S03]="S03-silent-schema-drift"
)

declare -A SCENARIO_SYMPTOMS=(
  [S01]="After a price update, ~15% of requests see the old price for 30-90 seconds.
  Cache hit rate is 98% (looks healthy). Events delivered in <200ms (looks healthy).
  No errors in any service logs. The bug is intermittent and timing-dependent.
  Customer complaint: 'I changed the price 2 minutes ago and some users still see the old one.'

  Services running:
    API Gateway:       http://localhost:8000   GET /price/P001
    Order Service:     http://localhost:8001   POST /price/P001 {\"price\": 49.99}
    RabbitMQ Console:  http://localhost:15672  (guest/guest)
    Redis:             localhost:6379"

  [S02]="During a simulated maintenance window on the downstream service, the API server's
  success rate drops dramatically and request counts at the downstream service are
  far higher than inbound requests to the API server.
  No errors in logs beyond the expected 503s. The system is generating far more
  downstream calls than there are inbound requests.

  Services running:
    API Server:   http://localhost:8010   POST /submit {\"job_id\": \"test-1\"}
    Downstream:   http://localhost:8011   GET  /stats
    Stats:        http://localhost:8010/stats  (shows inbound vs downstream call counts)

  Trigger test:
    curl -s -X POST http://localhost:8010/stats/reset
    for i in \$(seq 1 10); do curl -s -X POST http://localhost:8010/submit -H 'Content-Type: application/json' -d \"{\\\"job_id\\\":\\\"job-\$i\\\"}\" & done; wait
    curl -s http://localhost:8010/stats | python3 -m json.tool"

  [S03]="After a database migration added 'priority' and 'throttle_seconds' columns,
  Service B is not applying priority filtering or throttling.
  No errors anywhere. All health checks pass. Direct DB queries show data is correct.
  The features randomly start working for ~1 hour then stop again.

  Setup steps:
    1. Snapshot the schema (before migration): curl -s -X POST http://localhost:8021/admin/snapshot-schema
    2. Run the migration:                      curl -s -X POST http://localhost:8020/admin/migrate
    3. Check Service B's view of the schema:   curl -s http://localhost:8021/schema
    4. Check actual DB schema:                 curl -s http://localhost:8020/schema
    5. Dispatch a notification:                curl -s -X POST http://localhost:8021/dispatch/1

  Services running:
    Service A (schema owner):  http://localhost:8020
    Service B (dispatcher):    http://localhost:8021
    Redis:                     localhost:6380"
)

usage() {
  echo "Usage:"
  echo "  $0 <SCENARIO>                         Start scenario (S01, S02, S03)"
  echo "  $0 <SCENARIO> --down                  Tear down scenario"
  echo "  $0 --score <SCENARIO> <trajectory>    Score a trajectory file"
  echo ""
  echo "Examples:"
  echo "  $0 S01"
  echo "  $0 S01 --down"
  echo "  $0 --score S01 my-trajectory.json"
  exit 1
}

score_trajectory() {
  local scenario="$1"
  local trajectory="$2"
  if [[ ! -f "$trajectory" ]]; then
    echo "Error: trajectory file not found: $trajectory"
    exit 1
  fi
  echo "Scoring trajectory $trajectory against scenario $scenario..."
  python3 "$CHALLENGES_DIR/scoring/score.py" \
    --trajectory "$trajectory" \
    --scenario "$scenario"
}

start_scenario() {
  local scenario="$1"
  local dir_name="${SCENARIO_DIRS[$scenario]:-}"
  if [[ -z "$dir_name" ]]; then
    echo "Error: unknown scenario '$scenario'. Valid: ${!SCENARIO_DIRS[*]}"
    exit 1
  fi

  local scenario_dir="$CHALLENGES_DIR/$dir_name"
  echo ""
  echo "=========================================="
  echo " Debug-Bench: $scenario"
  echo "=========================================="
  echo ""
  echo "Starting Docker environment..."
  docker compose -f "$scenario_dir/docker-compose.yml" up -d --build

  echo ""
  echo "Waiting for health checks..."
  local max_wait=90
  local elapsed=0
  local all_healthy=false
  while [[ $elapsed -lt $max_wait ]]; do
    local unhealthy
    unhealthy=$(docker compose -f "$scenario_dir/docker-compose.yml" ps --format json 2>/dev/null \
      | python3 -c "
import sys, json
lines = sys.stdin.read().strip()
# docker compose ps --format json outputs one JSON object per line
count = 0
for line in lines.splitlines():
    try:
        s = json.loads(line)
        health = s.get('Health', '')
        state = s.get('State', '')
        if state == 'running' and health not in ('healthy', ''):
            count += 1
    except Exception:
        pass
print(count)
" 2>/dev/null || echo "0")
    if [[ "$unhealthy" == "0" ]]; then
      all_healthy=true
      break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo -n "."
  done
  echo ""

  if [[ "$all_healthy" == "false" ]]; then
    echo "Warning: some services may not be fully healthy after ${max_wait}s."
    echo "Check with: docker compose -f $scenario_dir/docker-compose.yml ps"
  else
    echo "All services healthy."
  fi

  echo ""
  echo "=========================================="
  echo " SCENARIO: $scenario"
  echo " SYMPTOM"
  echo "=========================================="
  echo ""
  echo "${SCENARIO_SYMPTOMS[$scenario]}"
  echo ""
  echo "=========================================="
  echo " Investigate the running system above."
  echo " When done, record your trajectory to trajectory.json"
  echo " Then run: $0 $scenario --down"
  echo " Score:    $0 --score $scenario trajectory.json"
  echo "=========================================="
  echo ""
}

stop_scenario() {
  local scenario="$1"
  local dir_name="${SCENARIO_DIRS[$scenario]:-}"
  if [[ -z "$dir_name" ]]; then
    echo "Error: unknown scenario '$scenario'."
    exit 1
  fi
  local scenario_dir="$CHALLENGES_DIR/$dir_name"
  echo "Stopping $scenario environment..."
  docker compose -f "$scenario_dir/docker-compose.yml" down -v
  echo "Done."
}

# Argument parsing
if [[ $# -eq 0 ]]; then
  usage
fi

if [[ "$1" == "--score" ]]; then
  [[ $# -lt 3 ]] && usage
  score_trajectory "$2" "$3"
elif [[ $# -ge 2 && "$2" == "--down" ]]; then
  stop_scenario "$1"
elif [[ $# -eq 1 ]]; then
  start_scenario "$1"
else
  usage
fi
