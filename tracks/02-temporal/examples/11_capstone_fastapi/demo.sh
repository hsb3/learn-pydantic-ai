#!/usr/bin/env bash
# Drive the capstone end-to-end via curl. Run after `make temporal-11-up`.
#
# 1. POST a topic -> get a workflow_id
# 2. Poll GET until status=awaiting_approval
# 3. POST approval signal
# 4. Poll until status=completed, print the report

set -euo pipefail

API="${API:-http://localhost:8001}"
TOPIC="${TOPIC:-Germany}"

echo "POST $API/research  topic=$TOPIC"
WF_ID=$(curl -s -X POST "$API/research" \
  -H 'content-type: application/json' \
  -d "{\"topic\": \"$TOPIC\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["workflow_id"])')
echo "workflow_id=$WF_ID"
echo ""

echo "Polling until status=awaiting_approval ..."
for i in $(seq 1 90); do
  RESP=$(curl -s "$API/research/$WF_ID")
  STATUS=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  printf '  [%02d] status=%s\n' "$i" "$STATUS"
  if [ "$STATUS" = "awaiting_approval" ]; then
    break
  fi
  sleep 1
done

if [ "$STATUS" != "awaiting_approval" ]; then
  echo "Timed out waiting for approval gate. Last response: $RESP"
  exit 1
fi

echo ""
echo "Draft so far:"
echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["draft"])'
echo ""

echo "POST $API/research/$WF_ID/approve"
curl -s -X POST "$API/research/$WF_ID/approve" \
  -H 'content-type: application/json' \
  -d '{"note": "ship it"}' >/dev/null
echo ""

echo "Polling until status=completed ..."
for i in $(seq 1 30); do
  RESP=$(curl -s "$API/research/$WF_ID")
  STATUS=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  printf '  [%02d] status=%s\n' "$i" "$STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 1
done

echo ""
echo "Final report:"
echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["final_report"])'
