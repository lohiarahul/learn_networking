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

# The cgroup directory for a Pod, on the node running it. Not guessable: the kubelet writes the UID
# with underscores rather than dashes, and the slice path carries the QoS class, so
# kubelet.slice/kubelet-kubepods.slice/kubelet-kubepods-burstable.slice/kubelet-kubepods-burstable-pod<uid_>.slice
# Echoes "<node> <dir>" so callers can docker exec against the right machine.
pod_cgroup() {
  local ns="$1" name="$2"
  local node uid dir
  node=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.spec.nodeName}' 2>/dev/null)
  uid=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.metadata.uid}' 2>/dev/null | tr '-' '_')
  [ -n "$node" ] && [ -n "$uid" ] || return 1
  dir=$(docker exec "$node" sh -c \
    "find /sys/fs/cgroup -maxdepth 6 -type d -name '*${uid}*' 2>/dev/null | head -1")
  [ -n "$dir" ] || return 1
  printf '%s %s' "$node" "$dir"
}
# Exported because it is the one helper a check calls from inside `bash -c`, and a shell function is
# not inherited by a child shell unless it is.
export -f pod_cgroup

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
  local ns=(); [ -n "${3:-}" ] && ns=(-n "$3")
  if ! out=$(kubectl "${ns[@]}" rollout status "deployment/$d" --timeout=30s 2>&1); then
    bad "the rollout of $d completed" "$out"; return 1
  fi
  local up avail
  up=$(kubectl "${ns[@]}" get deploy "$d" -o jsonpath='{.status.updatedReplicas}' 2>/dev/null)
  avail=$(kubectl "${ns[@]}" get deploy "$d" -o jsonpath='{.status.availableReplicas}' 2>/dev/null)
  if [ "${up:-0}" = "$want" ] && [ "${avail:-0}" = "$want" ]; then
    ok "all $want replicas are running the *current* template (updated=$up, available=$avail)"
  else
    bad "all $want replicas are running the current template" \
        "updatedReplicas=${up:-0}, availableReplicas=${avail:-0} — an old ReplicaSet is still carrying the traffic"
    return 1
  fi
}

# The Act V discriminator, as an assertion. `kubectl get endpoints` prints `<none>` both when the
# selector matched no Pod and when every Pod it matched is unready — two completely different bugs
# behind one symptom. The EndpointSlice is the object that keeps them apart, because it lists the
# address *and* its readiness condition, so this counts only addresses a Service would actually send
# traffic to and ignores the rest.
endpoints_ready() {
  local ns="$1" svc="$2" want="$3" n
  n=$(kubectl -n "$ns" get endpointslice -l "kubernetes.io/service-name=$svc" \
        -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{" "}{.addresses[0]}{"\n"}{end}' \
        2>/dev/null | grep -c '^true ')
  if [ "${n:-0}" -eq "$want" ]; then ok "the Service has $want endpoint(s) that are present *and* ready"
  else
    local all; all=$(kubectl -n "$ns" get endpointslice -l "kubernetes.io/service-name=$svc" \
        -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"="}{.addresses[0]}{" "}{end}' 2>/dev/null)
    bad "the Service has $want ready endpoint(s)" "ready-count=${n:-0}; slice says: ${all:-<no slice at all>}"
    return 1
  fi
}

# Does the Service carry traffic *by name*, from a Pod that did not exist when you fixed it? This is
# the Act V claim in one probe: DNS answered, kube-proxy had somewhere to DNAT to, the filter let it
# through and the app replied. The Pod is named `probe` so it carries `run=probe` — the same label the
# drills' own probe Pods wear, which matters wherever a NetworkPolicy is the thing being tested.
svc_answers() {
  local ns="$1" svc="$2" port="${3:-80}" name=probe phase="" i
  kubectl -n "$ns" delete pod "$name" --ignore-not-found >/dev/null 2>&1
  kubectl -n "$ns" run "$name" --image=busybox:1.36 --restart=Never \
          --command -- sh -c "wget -q -T 8 -O /dev/null http://$svc:$port/" >/dev/null 2>&1
  for i in $(seq 1 40); do
    phase=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.status.phase}' 2>/dev/null)
    case "$phase" in Succeeded|Failed) break;; esac
    sleep 1
  done
  local why; why=$(kubectl -n "$ns" logs "$name" 2>&1 | tr '\n' ' ')
  kubectl -n "$ns" delete pod "$name" --ignore-not-found --wait=false >/dev/null 2>&1
  if [ "$phase" = "Succeeded" ]; then
    ok "a brand-new Pod reached http://$svc:$port/ by name"
  else
    bad "a brand-new Pod reached http://$svc:$port/ by name" "${why:-the probe Pod sat in '${phase:-<no phase>}'}"
    return 1
  fi
}

# ------------------------------------------------- Act VIII: certificates, locally

# Act VIII needs no cluster and no container. It needs OpenSSL 3.x and the small PKI its diagnose page
# builds in ${TMPDIR}/drills, so these verifiers run right there — and, like Act IX's, they run the
# experiment the answer predicts rather than checking a repair, because none of the six drills breaks
# anything. A certificate that fails to verify is not a fault; it is a correct answer to a question the
# reader has to identify.
PKI="${TMPDIR:-/tmp}/drills"

pki_ready() {
  if [ ! -d "$PKI" ]; then
    bad "the drill PKI exists in $PKI" "run the diagnose page's setup block first — the six drills share one PKI"
    return 1
  fi
  local missing=""
  for f in root.crt root.key int.crt int.key leaf.crt leaf.key; do
    [ -s "$PKI/$f" ] || missing="$missing $f"
  done
  if [ -n "$missing" ]; then
    bad "the drill PKI is complete" "missing from $PKI:$missing"; return 1
  fi
  ok "the drill PKI is in place (root -> intermediate -> leaf)"
}

# OpenSSL 3.x, not LibreSSL. The diagnose page says so and two of the drills silently produce the wrong
# result without it, which is worse than failing.
openssl3() {
  local v; v=$(openssl version 2>/dev/null)
  case "$v" in
    OpenSSL\ 3*|OpenSSL\ 4*) ok "openssl is $v" ;;
    *) bad "openssl is OpenSSL 3.x" "found '${v:-nothing}' — LibreSSL lacks -not_before/-not_after and will not reproduce these drills"; return 1 ;;
  esac
}

# require, but with $PKI as the working directory, which is where every path in these drills is relative to.
pki_require() {
  local desc="$1"; shift
  require "$desc" sh -c "cd '$PKI' && { $*; }"
}

# ------------------------------------------------- Acts I-IV: the lab container

# Acts I to IV do not run against a cluster. They run inside one privileged container with its own
# namespaces, veths and NAT tables — so their verifiers cannot read anything from the host, and every
# assertion below goes through `docker exec` into that container.
#
# The container is conventionally named `lab`, because that is the `--name` every one of those
# diagnose pages tells you to use. Override with LAB=<name> if yours is called something else.
LAB=${LAB:-lab}

lab_up() {
  if docker exec "$LAB" true 2>/dev/null; then
    ok "the lab container ($LAB) is running"
  else
    bad "the lab container ($LAB) is running" \
        "start it the way the drill page says and keep it running while you verify: docker run --rm -it --privileged --network host --name $LAB netlab"
    return 1
  fi
}

# Run a shell command inside the lab and hand back its output. Exit status is the command's.
#
# If you need to pipe a script *in* — a python heredoc, say — use `docker exec -i`. Without `-i` the
# container gets no stdin at all and the interpreter reads an empty program, which does not error: it
# succeeds, prints nothing, and the check fails with "no output" for a reason that is nowhere near
# the check.
lab() { docker exec "$LAB" sh -c "$1" 2>&1; }

# require, but inside the lab.
lab_require() {
  local desc="$1"; shift
  require "$desc" docker exec "$LAB" sh -c "$*"
}

# Is this lab's uplink a real L3/L2 path, or a userspace stack pretending to be one?
#
# It matters because two Act I-IV drills cannot reproduce their symptom behind a userspace uplink:
# poisoning the gateway's MAC costs nothing when frames are not delivered by their L2 header, and a
# missing MASQUERADE costs nothing when the source address is rewritten outside netfilter. Both then
# produce a *false pass* on the obvious reachability check, which is worse than a failure.
#
# The tell is policy routing: Docker Desktop's VM puts the default route in table 2 and leaves the main
# table without one. Heuristic, but a measured one — and it is the same fact that breaks
# `ip route show default`.
lab_uplink_is_real() {
  ! docker exec "$LAB" sh -c "ip rule show 2>/dev/null | grep -q 'lookup 2'" 2>/dev/null
}

# require, but inside one of the drill's network namespaces. This is the shape most Act IV checks
# take, because the whole act is about a packet's view of the world changing with where it stands.
ns_require() {
  local desc="$1" ns="$2"; shift 2
  require "$desc" docker exec "$LAB" ip netns exec "$ns" sh -c "$*"
}

# The lab's own uplink and gateway, and note *how* they are derived, because the obvious way is wrong
# here. `ip route show default` reads only the **main** table, and on Docker Desktop's VM the default
# route lives in a separate policy-routing table — `ip rule show` reveals a `lookup 2` — so `show
# default` prints **nothing at all** and every `$(...)` built on it silently becomes an empty string.
# `ip route get <dst>` asks the kernel which route it would actually use, whichever table holds it.
# Act II lesson 01 explains this; these two functions are it, applied.
lab_uplink()  { docker exec "$LAB" sh -c "ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if(\$i==\"dev\"){print \$(i+1); exit}}'" 2>/dev/null | head -1; }
lab_gateway() { docker exec "$LAB" sh -c "ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if(\$i==\"via\"){print \$(i+1); exit}}'" 2>/dev/null | head -1; }

# ------------------------------------------------- Act IX: identity, over the wire

# Act IX is the one act where nothing is broken, so its verifiers cannot check a repair. What they can
# do is run the experiment the answer predicts — grant a permission and watch an authentication failure
# refuse to move, revoke a permission and watch it land in the same second an identity would have taken
# ten. That is a stronger check than it sounds: a wrong explanation predicts the wrong result.
#
# Every request goes out through curl and not kubectl, for the reason drill 4 exists: kubectl sends the
# kubeconfig's client certificate too, and the certificate authenticator runs first, so a test that
# uses kubectl is testing the wrong credential and cannot tell.
#
# Call this *bare*, never through `require` — `require` runs its command inside `$(...)`, and a
# subshell's variable assignments do not survive it. Which is why it asserts for itself.
act9_env() {
  API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null)
  CA="${TMPDIR:-/tmp}/verify-act9-ca.crt"
  kubectl config view --minify --raw \
    -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' 2>/dev/null | base64 -d > "$CA"
  URL="$API/api/v1/namespaces/default/pods"
  if [ -n "$API" ] && [ -s "$CA" ]; then
    ok "a kubeconfig that reaches the cluster ($API)"
  else
    bad "a kubeconfig that reaches the cluster" \
        "could not read a server URL and a CA out of the current context — every check below sends its own request, so they all depend on this"
    return 1
  fi
}

# The HTTP code the API server gives this bearer token, and nothing else in the request.
#
# The empty-token guard is not defensive padding. `Authorization: Bearer ` with nothing after it is a
# well-formed request from `system:anonymous`, so it comes back **403** — a plausible-looking answer to
# a question that was never asked. Every failure in this file that took real debugging was that: a
# token that failed to mint, and a 403 that looked like a permissions result.
api_status() {
  [ -n "${1:-}" ] || { printf 'no-token-was-minted'; return 0; }
  curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -H "Authorization: Bearer $1" "$URL"
}

# Same, but allow the authorizer's caches a moment to catch up before believing the answer. Used only
# where a grant has just been written; revocation needs no window at all, which is itself a drill.
api_status_settles() {
  local want="$1" tok="$2" i c
  for i in $(seq 1 10); do
    c=$(api_status "$tok"); [ "$c" = "$want" ] && break
    sleep 1
  done
  printf '%s' "$c"
}

# Who does the API server think sent this? Asking the server is the only way to be sure, because the
# question "which of the credentials I sent was believed" has no local answer.
api_whoami() {
  [ -n "${1:-}" ] || { printf ''; return 0; }
  curl -s --cacert "$CA" -H "Authorization: Bearer $1" -H 'Content-Type: application/json' \
    -X POST "$API/apis/authentication.k8s.io/v1/selfsubjectreviews" \
    -d '{"apiVersion":"authentication.k8s.io/v1","kind":"SelfSubjectReview"}' 2>/dev/null \
  | python3 -c 'import sys,json
try: print(json.load(sys.stdin)["status"]["userInfo"]["username"])
except Exception: print("")' 2>/dev/null
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
