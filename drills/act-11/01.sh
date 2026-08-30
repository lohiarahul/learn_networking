# Act XI drill 1 — a panel and an alert both go quiet
HINT='name the relationship between the scrape interval and the range window in the query, and
say what rate() needs at minimum from a window to return anything at all.'
CAUSE_SHA='30c482cf3aa087d73fb466fe1b42ab8aa6ae72d879dd15b3cfe6c1f8370cedea
89d55fb0ff7750e2b3ec5c33328a247d7af6993e0de1c05da6453dab6622353e
9449d5991414d53f2c26fbdeb357f158e42deed19279a8dd09a260ce24a182f9
8a7d0bdb91c6cfc75d629fb93be35beaaf222649b0e268a861539f3738124c61
b54a80ba108744b7b43c777c092135865f6d2ad4a13e44e400df6edf14dc6738'

PROM=${PROM:-diag-prom}

prom_up() {
  if docker exec "$PROM" true 2>/dev/null; then ok "the drill's Prometheus ($PROM) is running"
  else bad "the drill's Prometheus ($PROM) is running" "start it the way the diagnose page's Bench D block says"; return 1; fi
}

prom_query() {
  docker exec "$PROM" wget -qO- "http://localhost:9090/api/v1/query?query=$1" 2>/dev/null
}

scrape_interval_seconds() {
  # Prometheus normalises the config it echoes back — 60s becomes 1m — so parse whatever
  # unit it chose rather than assuming seconds.
  docker exec "$PROM" wget -qO- 'http://localhost:9090/api/v1/status/config' 2>/dev/null \
    | python3 -c "
import sys,json,re
y=json.load(sys.stdin)['data']['yaml']
m=re.search(r'scrape_interval:\s*(\d+)(ms|s|m|h)', y)
if not m:
    print(0)
else:
    n, unit = int(m.group(1)), m.group(2)
    mult = {'ms': 0, 's': 1, 'm': 60, 'h': 3600}[unit]
    print(n * mult)
" 2>/dev/null
}

wide_window_has_data() {
  local interval; interval=$(scrape_interval_seconds)
  [ "${interval:-0}" -gt 0 ] || { bad "the scrape interval could be read from the running config" "no scrape_interval found"; return 1; }
  local window=$((interval * 3))
  local out; out=$(prom_query "rate%28hits_total%5B${window}s%5D%29")
  local n; n=$(printf '%s' "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']['result']))" 2>/dev/null)
  if [ "${n:-0}" -ge 1 ]; then ok "a window at least 3x the scrape interval (${window}s) returns a real value"
  else bad "a window at least 3x the scrape interval returns a real value" "still empty — wait longer for samples to accumulate, then retry"; return 1; fi
}

prom_up && wide_window_has_data
answer_check "${ANSWER:-}"
verdict
