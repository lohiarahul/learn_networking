#!/usr/bin/env bash
# drills/lib.sh — the assertions every drill verifier is built from.
#
# Why this file exists
# -------------------
# Every drill in this course ends with a `<details>Reveal` block, and a reveal is graded by the
# learner. That is the weakest link in the whole repository: reading an explanation and believing you
# would have got there is the most reliable way a self-study learner overestimates themselves. The
# harness that checks the *author* (`tools/check_pedagogy.py`, `tools/probe-lab.py`) was never pointed
# at the *learner*. This is that harness.
#
# Two rules shape everything below.
#
# 1. **Verify by function, not by configuration.** "The manifest file is back" is a statement about a
#    file. "A brand-new Pod acquired a `spec.nodeName` within 40 seconds" is a statement about a
#    scheduler that is actually reconciling. Only the second one is a fix. Every check here that can
#    be written as a live probe is written as a live probe.
#
# 2. **The verifier must not be a spoiler.** These files sit in the repo in plain sight, and a
#    verifier that names the cause is a second reveal with a nicer interface. So the expected answer
#    is stored as a **SHA-256 of its normalised form** and never as text. You cannot read the answer
#    out of this repository; you can only be told whether yours matched. That is also what makes the
#    check meaningful — a cluster someone restored by pasting the `Fix it` block, or by deleting and
#    recreating it, passes the state checks and fails the drill, which is the correct outcome.
set -uo pipefail

_PASS=0; _FAIL=0
_c() { [ -t 1 ] && printf '%s' "$1" || true; }
GREEN=$(_c $'\033[32m'); RED=$(_c $'\033[31m'); DIM=$(_c $'\033[2m'); OFF=$(_c $'\033[0m')

ok()   { _PASS=$((_PASS+1)); printf '  %s✓%s %s\n' "$GREEN" "$OFF" "$1"; }
bad()  { _FAIL=$((_FAIL+1)); printf '  %s✗%s %s\n' "$RED" "$OFF" "$1"; [ $# -gt 1 ] && printf '      %s%s%s\n' "$DIM" "$2" "$OFF"; return 0; }
note() { printf '    %s%s%s\n' "$DIM" "$1" "$OFF"; }

# require "<what should be true>" <command...>
require() {
  local desc="$1"; shift
  local out
  if out=$("$@" 2>&1); then ok "$desc"; else bad "$desc" "${out:-(command exited non-zero)}"; fi
}

# require_eq "<what>" "<expected>" <command...>
require_eq() {
  local desc="$1" want="$2"; shift 2
  local got; got=$("$@" 2>&1)
  if [ "$got" = "$want" ]; then ok "$desc"; else bad "$desc" "expected '$want', got '$got'"; fi
}

# ---------------------------------------------------------------- cluster probes

CP=${CP:-netlab-control-plane}
WORKER=${WORKER:-netlab-worker}

# The four static-pod manifests a kubeadm control plane runs from. Missing one is invisible until the
# cluster needs the thing that is missing, which is why every Kubernetes drill checks all four.
all_static_manifests() {
  local want="etcd.yaml kube-apiserver.yaml kube-controller-manager.yaml kube-scheduler.yaml"
  local got; got=$(docker exec "$CP" ls /etc/kubernetes/manifests/ 2>/dev/null | sort | tr '\n' ' ')
  local missing=""
  for m in $want; do case " $got " in *" $m "*) ;; *) missing="$missing $m";; esac; done
  if [ -n "$missing" ]; then bad "all four control-plane manifests present" "missing:$missing"; return 1; fi
  ok "all four control-plane manifests present"
}

api_answers() {
  local out; out=$(kubectl get --raw /readyz 2>&1)
  if [ "$out" = "ok" ]; then ok "the API server answers /readyz with ok"
  else bad "the API server answers /readyz with ok" "$out"; return 1; fi
}

control_plane_pods_ready() {
  local n; n=$(kubectl -n kube-system get pods -l tier=control-plane \
                 -o jsonpath='{range .items[*]}{.status.phase}{"\n"}{end}' 2>/dev/null | grep -c Running)
  if [ "${n:-0}" -ge 4 ]; then ok "four control-plane Pods Running ($n)"
  else bad "four control-plane Pods Running" "found ${n:-0}"; return 1; fi
}

nodes_ready() {
  local want="${1:-2}"
  local n; n=$(kubectl get nodes --no-headers 2>/dev/null | awk '$2=="Ready"' | wc -l | tr -d ' ')
  if [ "${n:-0}" -eq "$want" ]; then ok "$want node(s) Ready"
  else bad "$want node(s) Ready" "$(kubectl get nodes --no-headers 2>&1 | tr '\n' ';')"; return 1; fi
}

no_node_cordoned() {
  local out; out=$(kubectl get nodes --no-headers 2>/dev/null | grep -c SchedulingDisabled)
  if [ "${out:-0}" -eq 0 ]; then ok "no node left SchedulingDisabled"
  else bad "no node left SchedulingDisabled" "run 'kubectl uncordon <node>'"; return 1; fi
}

absent() {  # absent <human description> <kubectl args...>
  local desc="$1"; shift
  if kubectl "$@" >/dev/null 2>&1; then bad "$desc" "it is still there — the drill left debris"; return 1
  else ok "$desc"; fi
}

# The strongest single check in this file: does a *new* Pod get placed, and by whom. A file being back
# on disk proves nothing; a Pod acquiring a nodeName proves a scheduler is running and reconciling.
probe_scheduled() {
  local ns=${1:-default} name="verify-probe-$$"
  kubectl -n "$ns" run "$name" --image=busybox:1.36 --restart=Never \
          --command -- sh -c 'sleep 300' >/dev/null 2>&1
  local node="" i
  for i in $(seq 1 40); do
    node=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.spec.nodeName}' 2>/dev/null)
    [ -n "$node" ] && break
    sleep 1
  done
  kubectl -n "$ns" delete pod "$name" --wait=false --grace-period=0 --force >/dev/null 2>&1
  if [ -n "$node" ]; then ok "a brand-new Pod was scheduled (onto $node) — a scheduler is reconciling"
  else bad "a brand-new Pod was scheduled" "spec.nodeName stayed empty for 40s"; return 1; fi
}

# Does a controller still *write*? A stopped controller-manager leaves status fields frozen at their
# last-known-good value, so a Deployment can read 3/3 forever. Scale one and watch the field move.
probe_controller_writes() {
  local ns=default name="verify-ctl-$$"
  kubectl -n $ns create deployment "$name" --image=busybox:1.36 --replicas=1 \
          -- sh -c 'sleep 300' >/dev/null 2>&1
  local got="" i
  for i in $(seq 1 60); do
    got=$(kubectl -n $ns get deploy "$name" -o jsonpath='{.status.replicas}' 2>/dev/null)
    [ "${got:-0}" -ge 1 ] 2>/dev/null && break
    sleep 1
  done
  kubectl -n $ns delete deployment "$name" --wait=false >/dev/null 2>&1
  if [ "${got:-0}" -ge 1 ] 2>/dev/null; then ok "a controller wrote status on a new Deployment — the loop is running"
  else bad "a controller wrote status on a new Deployment" "status.replicas stayed empty for 60s"; return 1; fi
}

# `status.phase` is Running for a Pod whose containers are crash-looping — the phase is about the
# sandbox, not the processes — so a naive phase check passes on a CrashLoopBackOff. The Ready condition
# is the claim that cannot be faked: it requires every container to have passed its checks *now*.
pod_ready() {
  local ns="$1" name="$2"
  local s; s=$(kubectl -n "$ns" get pod "$name" \
        -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)
  if [ "$s" = "True" ]; then ok "pod/$name is Ready (every container, not just the sandbox)"
  else
    local st; st=$(kubectl -n "$ns" get pod "$name" --no-headers 2>/dev/null | awk '{print $2" "$3}')
    bad "pod/$name is Ready" "${st:-not found} — Ready=${s:-<none>}"; return 1
  fi
}

# Pin a Pod to one node and require it to actually *run* there. This is the strongest statement you
# can make about a single node without logging into it: a Pod reaching Running on node N means N's
# kubelet is up, talking to the API server, talking to its container runtime, and able to build a
# sandbox — four claims in one observation, and the four things that make a node NotReady.
pod_runs_on() {
  local node="$1" name="verify-on-$$" phase="" i
  kubectl run "$name" --image=busybox:1.36 --restart=Never \
    --overrides="{\"spec\":{\"nodeName\":\"$node\",\"tolerations\":[{\"operator\":\"Exists\"}]}}" \
    --command -- sh -c 'sleep 120' >/dev/null 2>&1
  for i in $(seq 1 60); do
    phase=$(kubectl get pod "$name" -o jsonpath='{.status.phase}' 2>/dev/null)
    [ "$phase" = "Running" ] && break
    sleep 1
  done
  local ip; ip=$(kubectl get pod "$name" -o jsonpath='{.status.podIP}' 2>/dev/null)
  kubectl delete pod "$name" --force --grace-period=0 --wait=false >/dev/null 2>&1
  if [ "$phase" = "Running" ]; then
    ok "a new Pod pinned to $node reached Running (IP $ip) — kubelet, runtime and CNI all answered"
  else
    bad "a new Pod pinned to $node reached Running" "it sat in '${phase:-<no phase>}' for 60s"
    return 1
  fi
  if [ -n "$ip" ]; then ok "and the CNI gave it an address"
  else bad "and the CNI gave it an address" "status.podIP was empty — the sandbox came up without networking"; return 1; fi
}

# A Deployment mid-rollout is the trap this whole file exists to avoid. During a stuck rollout the
# *old* ReplicaSet is still serving, so `status.readyReplicas` reads the full count, the Service has a
# full set of ready endpoints, and a curl succeeds — every naive check passes while the deploy is
# broken. The claim that is actually false is "the replicas that are ready are the ones I asked for".
# `updatedReplicas` is the field that says so, and `rollout status` is the one command that waits on it.
rollout_complete() {
  local d="$1" want="$2" out
  if ! out=$(kubectl rollout status "deployment/$d" --timeout=30s 2>&1); then
    bad "the rollout of $d completed" "$out"; return 1
  fi
  local up avail
  up=$(kubectl get deploy "$d" -o jsonpath='{.status.updatedReplicas}' 2>/dev/null)
  avail=$(kubectl get deploy "$d" -o jsonpath='{.status.availableReplicas}' 2>/dev/null)
  if [ "${up:-0}" = "$want" ] && [ "${avail:-0}" = "$want" ]; then
    ok "all $want replicas are running the *current* template (updated=$up, available=$avail)"
  else
    bad "all $want replicas are running the current template" \
        "updatedReplicas=${up:-0}, availableReplicas=${avail:-0} — an old ReplicaSet is still carrying the traffic"
    return 1
  fi
}

# ---------------------------------------------------------------- the answer

# Normalise so that "the kube-scheduler", "Kube Scheduler" and "kube-scheduler" are one answer.
_norm() { printf '%s' "$1" | tr 'A-Z' 'a-z' | sed -e 's/^the //' | tr -cd 'a-z0-9'; }
_sha()  { printf '%s' "$1" | shasum -a 256 2>/dev/null | cut -d' ' -f1 \
                          || printf '%s' "$1" | sha256sum | cut -d' ' -f1; }

# answer_check "<the learner's answer>"  — CAUSE_SHA must already hold one hash per line.
answer_check() {
  local given="${1:-}"
  if [ -z "$given" ]; then
    bad "you named the cause" "re-run with your diagnosis as the last argument: $HINT"
    return 1
  fi
  local h; h=$(_sha "$(_norm "$given")")
  if printf '%s\n' "$CAUSE_SHA" | grep -qx "$h"; then
    ok "you named the cause correctly"
  else
    bad "you named the cause" "'$given' is not it. $HINT"
    return 1
  fi
}

verdict() {
  printf '\n'
  if [ "$_FAIL" -eq 0 ]; then
    printf '%sPASS%s — %d checks, and you named the cause yourself.\n' "$GREEN" "$OFF" "$_PASS"; exit 0
  fi
  printf '%sFAIL%s — %d passed, %d failed. Not done yet.\n' "$RED" "$OFF" "$_PASS" "$_FAIL"; exit 1
}
