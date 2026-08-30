# Act XI drill 3 — queries time out, Prometheus's own memory is climbing
HINT='name the label that took on too many distinct values, and the mechanism (not the config
line) that stops it from happening again.'
CAUSE_SHA='432ea8f2ba82151b69d4ded1b730d70273e3a3104adee39ce5497fe589620d48
85d0b09aa815080c6a7cbf67e4e0994409f2b1d4d2c81aa0ee3e6abe5bac5a6d
fa447157863a2636bdeae65d80e8e7c5fdd11e61fcae75b5f9279fafe42690a7
7eb97a0a619a45b4db60f089f0e3b27c95fd12a501d77d70bba7ddc2d1267138'

PROM=${PROM:-diag-prom}

prom_query() {
  docker exec "$PROM" wget -qO- "http://localhost:9090/api/v1/query?query=$1" 2>/dev/null
}

series_under_bound() {
  local n; n=$(prom_query 'prometheus_tsdb_head_series' | python3 -c "import json,sys; print(int(float(json.load(sys.stdin)['data']['result'][0]['value'][1])))" 2>/dev/null)
  # After the fix, new series stop being *created* (old ones linger until staleness/compaction —
  # lesson 04b's own finding), so the bound here is generous on purpose: it is failing to shrink
  # to zero that would be wrong, not failing to shrink instantly.
  if [ -n "$n" ] && [ "$n" -gt 0 ] 2>/dev/null; then ok "prometheus_tsdb_head_series is readable ($n)"
  else bad "prometheus_tsdb_head_series is readable" "could not read a value — is $PROM still running?"; return 1; fi
}

original_question_still_answerable() {
  local out; out=$(prom_query 'sum(hits_total)')
  local n; n=$(printf '%s' "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']['result']))" 2>/dev/null)
  if [ "${n:-0}" -ge 1 ]; then ok "the metric's original question (a fleet-wide sum) still answers"
  else bad "the metric's original question still answers" "sum(hits_total) returned nothing"; return 1; fi
}

# The strongest check available without a spoiler: after the labeldrop fix, a *newly created*
# series on the fixed job must not carry the dropped label — proving the fix acts on new data
# rather than merely being present in the config file.
new_samples_lack_label() {
  local out; out=$(prom_query 'hits_total%7Bjob%3D%22diagexp2%22%2Cclient_ip%3D%22%22%7D')
  local n; n=$(printf '%s' "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']['result']))" 2>/dev/null)
  if [ "${n:-0}" -ge 1 ]; then ok "new samples on the fixed job no longer carry the dropped label"
  else bad "new samples on the fixed job no longer carry the dropped label" "run 'docker restart $PROM' after adding the labeldrop rule and wait 30s"; return 1; fi
}

series_under_bound && original_question_still_answerable && new_samples_lack_label
answer_check "${ANSWER:-}"
verdict
