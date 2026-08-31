# Act IV drill 9 — "it has every capability there is and cannot create a file"
#
# Two traps this has to close, and both are ways of "fixing" it that destroy the lesson:
#
#   1. `chmod 777 /etc` or `chown 0 /etc/agent.log`. The first works and is a security incident; the
#      second looks right and makes it *worse*, because UID 0 outside is not in that map at all. So the
#      log file must end up owned by the UID the map points at, not by root, and not world-writable.
#   2. Restarting the agent without the user namespace. That also makes the writes succeed, and throws
#      away the containment the namespace was providing. So the agent must still be in a user namespace
#      whose map is NOT the identity map.
#
# The last check is the functional one: the log has to be *growing*, which only a live agent that can
# actually open the file produces.
HINT='say what the process is, in terms of the file in /proc that reconciles the three readings.'
CAUSE_SHA='cefa42ccf86689f827f0776c5e3ba0f66cfbbf73a98b0777aa23cba45b9b7006
8a0afa87320328c87a6a7ccfaacdbd28aea6849302138974d812324b2f7a7633
2390b292d34ee479e8d1b2848c0b0446dae515b8e839a73d84d801072529dd0d
5b485323d42fc39e09f85fa9e1f82e4a08cf4e6a9e8fd7d2a33262b3780f6490
d26375f1ee423fcda76106f0267101164054962e5bea2fbe2aaac5dedc9f0039
d7a6af7d5b03bed356f7ae6ee1f6940d67dd02d0c5ac2432524ca4808b04c6b3
8a8a9e7d125ad763f6fe1724b00ea52979504892c35822e851c67cf26cc703e5
062755fa9a8d5e890dfc88b37d937540f406b5632cdaff6e624fcb471788fb8f'

lab_up
lab_require "the agent from the ticket is still running" \
  'test -f /tmp/agent.pid && kill -0 $(cat /tmp/agent.pid) 2>/dev/null'

# Configuration check, but a necessary one: the containment must not have been the thing you removed.
lab_require "and it is still in a user namespace with a non-identity map (you did not fix this by removing the namespace)" \
  'PID=$(cat /tmp/agent.pid); m=$(cat /proc/$PID/uid_map);
   echo "$m" | grep -qE "^ *0 +[1-9][0-9]* +[0-9]+$"'

lab_require "the log file is owned by the UID the map points at, not by root" \
  'PID=$(cat /tmp/agent.pid); out=$(awk "{print \$2; exit}" /proc/$PID/uid_map);
   own=$(stat -c %u /etc/agent.log 2>/dev/null); [ -n "$own" ] && [ "$own" = "$out" ]'

# The incident-shaped fix has to fail. /etc must not have been opened up to everyone.
lab_require "and you did not do it by making the directory or the file world-writable" \
  '! [ -w /etc ] || true;
   perms=$(stat -c %a /etc/agent.log 2>/dev/null); case "$perms" in *7|*6|*3|*2) exit 1;; esac;
   dperm=$(stat -c %a /etc); case "$dperm" in *7|*6|*3|*2) exit 1;; esac'

# Function: the agent is actually appending now. Two reads, four seconds apart.
lab_require "the agent is appending to it — the log grows while you watch" \
  'a=$(wc -l < /etc/agent.log 2>/dev/null || echo 0); sleep 4;
   b=$(wc -l < /etc/agent.log 2>/dev/null || echo 0); [ "$b" -gt "$a" ]'

answer_check "${ANSWER:-}"
verdict
