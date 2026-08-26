# Act I drill 2 — "it leaks, and a restart fixes it for a while"
HINT='name what the process runs out of. It is the thing lesson 01 said a process holds a table of.'
CAUSE_SHA='fc1b24b3f5d81d90b0aee0cbd4b0d1ee671a773e7ac3637c39a0adb1a0bb4261
d91b0ce77caabf0a5934863a19b563601dfea546969255bd62e6cfde5c045b1a
aec6023c9be4af2686cf5d99f08f36ecaeae9b0174cd5307ebb31d8ba7a58a45
310ff200149b44a32f124023d7caba19a1a890763a980606813d3a3d4a085d36
461a7ec03e810e9213d15851cb1b8d5a935434a0c2269e010431e7e276e586a8'

# The only honest check for a leak is to measure it, so this one does: count the server's open
# descriptors, make twenty connections, count again. A fixed server ends where it started; the drill's
# server ends twenty higher. `ss` cannot tell you this and neither can the log — /proc/<pid>/fd can.
lab_up
PID=$(lab 'ss -tlnp 2>/dev/null | grep ":8080" | sed -n "s/.*pid=\([0-9]*\).*/\1/p" | head -1')
if [ -z "$PID" ]; then
  bad "a server is listening on 8080 to measure" \
      "nothing is listening — run this while your fixed server is still up, before the drill's kill"
else
  BEFORE=$(lab "ls /proc/$PID/fd 2>/dev/null | wc -l" | tr -d ' ')
  lab 'for i in $(seq 1 20); do curl -s -o /dev/null --max-time 2 127.0.0.1:8080 || true; done' >/dev/null 2>&1
  sleep 2
  AFTER=$(lab "ls /proc/$PID/fd 2>/dev/null | wc -l" | tr -d ' ')
  GREW=$(( ${AFTER:-0} - ${BEFORE:-0} ))
  if [ "$GREW" -le 3 ]; then
    ok "twenty connections later the process holds $AFTER descriptors, up $GREW from $BEFORE — it lets go"
  else
    bad "the process releases its descriptors" \
        "it went from $BEFORE to $AFTER over twenty connections (+$GREW) — every accepted connection is still held"
  fi
fi
answer_check "${ANSWER:-}"
verdict
