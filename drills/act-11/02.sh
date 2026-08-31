# Act XI drill 2 — a dashboard flat green, an alert that never fired, nothing unhealthy
HINT='say what a comparison against a series that was never scraped returns, and name the
function that asks "does this exist at all" instead of "what is its value".'
CAUSE_SHA='84fff65228cc49b321400c561a312e9ca49f67eba64dcc0832213202d0d15183
cea67dd5f4eebb58744e9573b8b97e66aab2b676ffec3af4fe2602f3520d8f35
da0399f26f704d7364ebf647e4a0759cdd8bac2a795273417e45cd422e382a8c
9f226eb645f557925102252ea263418ee82eeb47acc10a7b46fe12f658a57b06
1a314e7e39da808dad4a2520b2626b15c9cf2c0cb9dc1a199a8504fd3c8e33b2'

# There is no state to repair here either — the point is that a threshold alert against a
# genuinely absent series cannot fire, ever, no matter how long you wait, and that absent()
# is a different question rather than a bigger number. Reproduce both halves live.
absence_is_not_false() {
  local n="verify-drill2-$$"
  docker rm -f "$n" >/dev/null 2>&1
  docker run -d --name "$n" --network kind prom/prometheus:v3.0.1 >/dev/null 2>&1
  sleep 5
  local empty
  empty=$(docker exec "$n" wget -qO- 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22neverscraped%22%7D' 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['data']['result']))" 2>/dev/null)
  local absent_val
  absent_val=$(docker exec "$n" wget -qO- 'http://localhost:9090/api/v1/query?query=absent(up%7Bjob%3D%22neverscraped%22%7D)' 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['result'][0]['value'][1])" 2>/dev/null)
  docker rm -f "$n" >/dev/null 2>&1
  if [ "${empty:-}" != "0" ]; then
    bad "up{job=\"neverscraped\"} returns an empty result, not a zero value" "got result array length '${empty:-<none>}' — is docker/prom/prometheus:v3.0.1 reachable?"
    return 1
  fi
  ok "up{job=\"neverscraped\"} returns nothing at all — a comparison against it can never be true"
  if [ "${absent_val:-}" = "1" ]; then
    ok "absent(up{job=\"neverscraped\"}) correctly returns 1 — this is the function a real alert needs"
  else
    bad "absent(up{job=\"neverscraped\"}) returns 1" "got '${absent_val:-<none>}'"
    return 1
  fi
}

absence_is_not_false
answer_check "${ANSWER:-}"
verdict
