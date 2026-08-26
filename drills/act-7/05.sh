# Act VII drill 5 — "the cron job hasn't run and nothing is wrong"
HINT='name the CronJob field that turned a slow job into no jobs at all — or the value it was set to.'
CAUSE_SHA='b254032406d3e4d7691402a621d38b3bea6b700dc5bbe002826f333ae337dd1a
76626ec9e79c1c457cae4f1a07bde35c7e4b33c222e9ad91d87ae95fc9e9eb12'

absent "the drill's CronJob is cleaned up" get cronjob report
require "no Job from this drill is left running" \
  bash -c '[ -z "$(kubectl get jobs -l drill=5 -o name 2>/dev/null)" ]'
require "and no Pod from it either" \
  bash -c '[ -z "$(kubectl get pods -l drill=5 -o name 2>/dev/null)" ]'
answer_check "${ANSWER:-}"
verdict
