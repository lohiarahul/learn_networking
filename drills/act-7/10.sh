# Act VII drill 10 — "the service is slow, and sometimes it just disappears"
HINT='two of the three symptoms were produced by the kernel. Name the component that produced the
third — the only one of the three that was Kubernetes making a decision.'
CAUSE_SHA='1ca4bc7eb9b3d6f1e205da9cfab437c89d3760d0765a29a6bcbccf4ad51a2cb1
01b1048759baa91ddf8e4641c07b44ec56d4e4364ab961d5fe0e872eebe138fb
d2d3ba10d807241ab55c91894aedd5107fff398f1e675840bd6c83d00e0301a2'

for p in hungry slow greedy; do
  pod_ready limitlab "$p"
done
# Ready is not enough for the OOM one: a Pod that is being killed and restarted is Ready in between.
# The claim is that the last thing that happened to it was not a kill.
require "the memory-hungry Pod has not been OOM-killed" \
  bash -c 'for q in ".status.containerStatuses[0].state.terminated.reason" \
                    ".status.containerStatuses[0].lastState.terminated.reason"; do
             r=$(kubectl -n limitlab get pod hungry -o jsonpath="{$q}" 2>/dev/null)
             [ "$r" = "OOMKilled" ] && exit 1
           done; exit 0'
# The throttled one is the whole point of the drill: its symptom leaves no trace in any Kubernetes
# object, so the only place it can be checked is the kernel counter the CFS controller increments.
require "the throttled Pod has stopped being throttled (cpu.stat, on the node)" \
  bash -c 'set -- $(pod_cgroup limitlab slow) || exit 1
           node=$1; dir=$2; [ -n "$dir" ] || exit 1
           a=$(docker exec "$node" sh -c "grep nr_throttled $dir/cpu.stat" | awk "{print \$2}")
           sleep 12
           b=$(docker exec "$node" sh -c "grep nr_throttled $dir/cpu.stat" | awk "{print \$2}")
           [ -n "$a" ] && [ "$a" = "$b" ]'
require "and its cpu.max is no longer the quota that was throttling it" \
  bash -c 'set -- $(pod_cgroup limitlab slow) || exit 1
           node=$1; dir=$2
           q=$(docker exec "$node" sh -c "cat $dir/cpu.max" | awk "{print \$1}")
           [ "$q" = "max" ] || [ "${q:-0}" -gt 5000 ]'
require "the evicted Pod is not Evicted any more" \
  bash -c '[ "$(kubectl -n limitlab get pod greedy -o jsonpath="{.status.reason}" 2>/dev/null)" != "Evicted" ]'
answer_check "${ANSWER:-}"
verdict
