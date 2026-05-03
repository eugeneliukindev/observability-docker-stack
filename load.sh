#!/usr/bin/env bash
# Sends a continuous stream of requests to the backend to generate
# realistic traffic — useful for populating Grafana dashboards.
#
# Usage:
#   ./load.sh              # default: http://localhost:8000, 20 req/s
#   ./load.sh 50           # 50 req/s
#   ./load.sh 10 http://localhost:8001

set -euo pipefail

RPS="${1:-20}"
BASE_URL="${2:-http://localhost:8000}"
INTERVAL=$(python3 -c "print(1/$RPS)")

ENDPOINTS=(
    "GET /"
    "GET /api/items"
    "GET /api/items/1"
    "GET /api/items/5"
    "GET /api/items/42"
    "GET /api/items/101"        # 404
    "GET /api/items/-1"         # 400
    "POST /api/items"
    "PUT /api/items/3"
    "PATCH /api/items/7"
    "DELETE /api/items/10"
    "DELETE /api/items/200"     # 404
    "POST /api/orders"
    "GET /api/orders/1234"
    "GET /api/orders/99999"     # 404
    "DELETE /api/orders/5678"
    "GET /api/random"
    "GET /api/slow"
    "GET /api/cpu"
    "GET /api/bad-request"      # 400
    "GET /api/server-error"     # 500
    "GET /api/exception"
    "GET /api/system-log"
)

ITEM_BODY='{"name": "Test Item", "price": 9.99}'
ORDER_BODY='{"item_id": 1, "quantity": 2}'

send() {
    local method="$1"
    local path="$2"
    local url="${BASE_URL}${path}"

    case "$method $path" in
        "POST /api/items")
            curl -sf -X POST "$url" -H "Content-Type: application/json" -d "$ITEM_BODY" -o /dev/null ;;
        "PUT /api/items/"*)
            curl -sf -X PUT "$url" -H "Content-Type: application/json" -d "$ITEM_BODY" -o /dev/null ;;
        "PATCH /api/items/"*)
            curl -sf -X PATCH "$url" -H "Content-Type: application/json" -d "$ITEM_BODY" -o /dev/null ;;
        "POST /api/orders")
            curl -sf -X POST "$url" -H "Content-Type: application/json" -d "$ORDER_BODY" -o /dev/null ;;
        *)
            curl -sf -X "$method" "$url" -o /dev/null ;;
    esac
    return 0
}

echo "Sending requests to $BASE_URL at ~${RPS} req/s. Ctrl+C to stop."

i=0
while true; do
    entry="${ENDPOINTS[$((i % ${#ENDPOINTS[@]}))]}"
    method="${entry%% *}"
    path="${entry#* }"

    send "$method" "$path" &

    i=$((i + 1))
    sleep "$INTERVAL"
done
