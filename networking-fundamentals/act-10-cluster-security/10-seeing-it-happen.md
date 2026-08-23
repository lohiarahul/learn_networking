# Seeing it happen

Nine lessons of refusals. A capability refuses a syscall, a seccomp filter refuses a syscall the capability would have allowed, a namespace label refuses a Pod, a policy refuses an image, WireGuard refuses a reader.

Lesson 09 finished by producing something none of them would touch. If somebody rewrote a node's published WireGuard key, every packet would still flow, every status line would still read `Wireguard`, `cilium-dbg` would still report a peer, and the single difference in the whole cluster would be *who else could read the traffic*. There is no request to deny, because the write was authorised. It was a `PATCH` on an object, by a principal permitted to `PATCH` that object.

This lesson is about the two controls in the act that refuse nothing at all, and the reason a system needs them anyway is exactly that: **the interesting failures are authorised.** An attacker who has got as far as using your API is not sending malformed requests. They are sending correct ones.

Lesson 03 already put a marker down for this. It measured three verbs on one predicate — `enforce` returns a 403, `warn` returns an HTTP warning header *and creates the object*, and `audit` "tells only the audit log". You have never looked at that log. This cluster may not have one.

> **Predict first —** four commitments. **(a)** Does this cluster have an audit log right now? Say yes or no before you check, then say what you would grep to find out. **(b)** You enable auditing at a level that records request bodies, because you want to know what people changed. Name a resource for which that decision is actively dangerous, and say why. **(c)** A completely idle two-node cluster — no users, no deployments, nothing happening. Roughly how many audit events per minute? Order of magnitude is enough, and the answer should bother you. **(d)** Somebody runs `kubectl exec` into a Pod and types three commands. How many of them are in the audit log?

### Prediction (a)

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

docker exec netlab-control-plane grep -c audit /etc/kubernetes/manifests/kube-apiserver.yaml
docker exec netlab-control-plane ls /var/log/kubernetes
```

```
0
ls: cannot access '/var/log/kubernetes': No such file or directory
```

Zero. Ten lessons of building and breaking a cluster — dropping capabilities, editing the API server four times, decrypting etcd, denying images, reading a bearer token off the wire — and **there is no record that any of it happened.** Everything you have done in this act is unreconstructable. That is the default, and lesson 07's kube-bench told you so: four of its eleven `FAIL`s were `--audit-log-*` flags, and this is the lesson they pointed at.

The reason for the default is worth stating, because it is not negligence. An audit log is a file that grows without bound on your control-plane node, containing everything anybody did, and Kubernetes has no idea where you want it shipped or what you can afford to keep. So the project ships the machinery and no policy, and a cluster with no policy writes nothing.

### The third edit

Lesson 03 promised you would do the three-part API server edit three times in this act. This is the third, and it needs the pattern twice over — a **read-only** mount for the policy and a **writable** one for the log.

First the policy, and read it before running it, because it is the whole design:

```bash
CP=netlab-control-plane
docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/ka-audit.bak
docker exec $CP mkdir -p /etc/kubernetes/audit /var/log/kubernetes
docker exec -i $CP sh -c 'cat > /etc/kubernetes/audit/policy.yaml' <<'EOF'
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
  - RequestReceived
rules:
  - level: None
    users: ["system:kube-scheduler", "system:kube-controller-manager", "system:apiserver"]
  - level: None
    resources:
    - group: ""
      resources: ["events"]
  - level: Metadata
    resources:
    - group: ""
      resources: ["secrets", "configmaps"]
  - level: Request
    verbs: ["create", "update", "patch", "delete"]
  - level: Metadata
EOF
```

Four things in there are decisions rather than boilerplate.

**`rules` is ordered and first-match-wins**, like an iptables chain from Act II — so the two `None` rules at the top are the ones doing the most work, and the final catch-all `Metadata` is what stops the policy from being a list of exceptions to nothing.

**The four levels are a ladder of how much of the request is kept**: `None` writes nothing, `Metadata` writes who/what/when/verdict, `Request` adds the body the client sent, and `RequestResponse` adds the body the server returned. Note there is a rule here that deliberately keeps Secrets at `Metadata` while everything else that writes gets `Request`. Hold that; it is prediction (b) and it gets its own section.

**`omitStages: RequestReceived`** halves the volume for free. Every request can produce an event when it arrives and again when it finishes, and the arrival event tells you nothing the completion event does not — except for requests that never finish, which is why the stage exists at all.

**The `None` on those three usernames** is the single largest lever in the file, and you will measure exactly how large.

Now the edit. Two mounts, two volumes, four flags:

```bash
docker exec netlab-control-plane cat /etc/kubernetes/manifests/kube-apiserver.yaml > /tmp/ka.yaml
python3 - <<'PY'
p="/tmp/ka.yaml"; t=open(p).read()
t = t.replace("    - --allow-privileged=true",
  "    - --allow-privileged=true"
  "\n    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml"
  "\n    - --audit-log-path=/var/log/kubernetes/audit.log"
  "\n    - --audit-log-maxsize=100"
  "\n    - --audit-log-maxbackup=3", 1)
t = t.replace("    volumeMounts:\n    - mountPath: /etc/ssl/certs",
  "    volumeMounts:"
  "\n    - mountPath: /etc/kubernetes/audit\n      name: audit-policy\n      readOnly: true"
  "\n    - mountPath: /var/log/kubernetes\n      name: audit-log\n      readOnly: false"
  "\n    - mountPath: /etc/ssl/certs", 1)
t = t.replace("  volumes:\n  - hostPath:",
  "  volumes:"
  "\n  - hostPath:\n      path: /etc/kubernetes/audit\n      type: DirectoryOrCreate"
  "\n    name: audit-policy"
  "\n  - hostPath:\n      path: /var/log/kubernetes\n      type: DirectoryOrCreate"
  "\n    name: audit-log"
  "\n  - hostPath:", 1)
open(p,"w").write(t); print("patched")
PY
docker exec -i netlab-control-plane sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/ka.yaml
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
docker exec netlab-control-plane sh -c 'ls -l /var/log/kubernetes/audit.log'
```

```
patched
healthy after 40s
-rw------- 1 root root 30523 Aug 23 02:30 /var/log/kubernetes/audit.log
```

Thirty kilobytes before you have done anything. Keep that in mind for prediction (c).

Notice what `--audit-log-maxsize=100` and `--audit-log-maxbackup=3` amount to: 400 MB of history, then it is gone. Those two flags are the whole retention policy, they are on the same node as the cluster they describe, and they are the reason real deployments ship this off the node immediately.

### One entry, read completely

Do the single most sensitive thing you can do to a cluster, and then look at what got written:

```bash
kubectl create ns seen
kubectl create secret generic db-creds -n seen --from-literal=password=hunter2
kubectl get secret db-creds -n seen -o jsonpath='{.data.password}' | base64 -d; echo
docker exec netlab-control-plane sh -c \
  'grep "\"name\":\"db-creds\"" /var/log/kubernetes/audit.log | grep "\"verb\":\"get\"" | tail -1' \
  | python3 -m json.tool
```

```json
{
    "kind": "Event", "apiVersion": "audit.k8s.io/v1",
    "level": "Metadata",
    "stage": "ResponseComplete",
    "requestURI": "/api/v1/namespaces/seen/secrets/db-creds",
    "verb": "get",
    "user": {
        "username": "kubernetes-admin",
        "groups": ["kubeadm:cluster-admins", "system:authenticated"],
        "extra": {
            "authentication.kubernetes.io/credential-id": [
                "X509SHA256=d6b667f1036a0ca8d4d4d9f455c2de882e2570fca5dde306bb92c5a2b8b39cda"
            ]
        }
    },
    "sourceIPs": ["172.19.0.1"],
    "userAgent": "kubectl/v1.36.4 (darwin/arm64) kubernetes/bb826b1",
    "objectRef": { "resource": "secrets", "namespace": "seen", "name": "db-creds" },
    "responseStatus": { "code": 200 },
    "requestReceivedTimestamp": "2026-08-23T02:30:11.751492Z",
    "stageTimestamp": "2026-08-23T02:30:11.752347Z",
    "annotations": {
        "authorization.k8s.io/decision": "allow",
        "authorization.k8s.io/reason": "RBAC: allowed by ClusterRoleBinding \"kubeadm:cluster-admins\" of ClusterRole \"cluster-admin\" to Group \"kubeadm:cluster-admins\""
    }
}
```

`hunter2` is not in there, which is the `Metadata` level working: **who read which Secret, not what was in it.** But go through the rest of it slowly, because three fields are payoffs of earlier acts and one of them is the single most useful field in Kubernetes security.

`user.username` and `groups` are Act IX's authentication result — the *outcome* of the process you took apart by hand, recorded. And `extra` names the specific credential: `X509SHA256=d6b667f1…` is the SHA-256 of the client certificate that authenticated. Not "an admin" — *that* certificate, distinguishable from every other certificate issued to the same subject. Act VIII had you compute SHA-256 digests of files by hand with `openssl dgst`; this is the same function over a certificate instead, and it is where that habit earns its keep — because "rotate the compromised credential" is only an actionable sentence once you know *which* credential.

Then `annotations`, and specifically `authorization.k8s.io/reason`:

> `RBAC: allowed by ClusterRoleBinding "kubeadm:cluster-admins" of ClusterRole "cluster-admin" to Group "kubeadm:cluster-admins"`

**The log records which rule allowed the request.** Act IX built RBAC's four-object model and then spent a lesson on the hard direction — *who can do X* — which requires enumerating every binding and is why `can-i --list` exists. This field answers the retrospective version exactly and for free: not "who could have", but "who did, and by which grant". When you are removing a permission and need to know whether anything actually uses it, this field is the evidence, and no amount of reading Roles will produce it.

### Lesson 03's third verb, finally read

Lesson 03 left `audit` as the one PSA verb it could not show you. Turn it on and violate it:

```bash
kubectl label ns seen pod-security.kubernetes.io/audit=restricted --overwrite
kubectl run bad -n seen --image=busybox:1.36 --restart=Never --command -- sh -c 'sleep 5'
sleep 4
docker exec netlab-control-plane sh -c \
  'grep "\"name\":\"bad\"" /var/log/kubernetes/audit.log | grep create | tail -1' \
  | python3 -c "
import json,sys
for k,v in json.load(sys.stdin).get('annotations',{}).items(): print(k,'=',v,'\n')
"
```

```
pod/bad created

authorization.k8s.io/decision = allow

authorization.k8s.io/reason = RBAC: allowed by ClusterRoleBinding "kubeadm:cluster-admins" ...

pod-security.kubernetes.io/audit-violations = would violate PodSecurity "restricted:latest":
  allowPrivilegeEscalation != false (container "bad" must set securityContext.allowPrivilegeEscalation=false),
  unrestricted capabilities (container "bad" must set securityContext.capabilities.drop=["ALL"]),
  runAsNonRoot != true (pod or container "bad" must set securityContext.runAsNonRoot=true),
  seccompProfile (pod or container "bad" must set securityContext.seccompProfile.type to "RuntimeDefault" or "Localhost")

pod-security.kubernetes.io/enforce-policy = privileged:latest
```

`pod/bad created`, and the complete verdict — the same four fields lessons 01 and 02 derived by experiment — exists in exactly one place on earth: an annotation on a line in a file on a node. That is what "tells only the audit log" meant, and it is why the third verb is useless in a cluster that has no log, which is the default.

Now the last annotation, which is quietly the most valuable thing in this section. `pod-security.kubernetes.io/enforce-policy = privileged:latest` — the enforce level **actually in effect for this request**.

Lesson 03 proved that enumerating namespace labels is an unsound audit in both directions: an unlabelled namespace was refusing privileged Pods because of a cluster-wide default, and a namespace labelled `enforce: baseline` ran a privileged Pod at full capabilities because a configuration file exempted it. The label and the behaviour had come apart, and nothing in the API said so.

This annotation is the thing that does say so. It is not the label; it is the *resolved* policy, after defaults and exemptions, recorded per request. So the sound way to answer "what is this cluster actually enforcing" is not to read labels — it is to read the audit log. That is a satisfying resolution to lesson 03's complaint, and it comes with a sting: the answer only exists for namespaces somebody has recently tried to create a Pod in.

### Prediction (b): the level is the whole design

You wanted request bodies so you could see what people changed. Try the obvious thing — `RequestResponse` on Secrets — and grep for the base64 of `hunter2`:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/audit/policy.yaml' <<'EOF'
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: [RequestReceived]
rules:
  - level: RequestResponse
    resources:
    - group: ""
      resources: ["secrets"]
  - level: Metadata
EOF
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done

kubectl get secret db-creds -n seen -o jsonpath='{.data.password}' >/dev/null
sleep 3
docker exec netlab-control-plane sh -c 'grep -c "aHVudGVyMg==" /var/log/kubernetes/audit.log'
docker exec netlab-control-plane sh -c 'grep "aHVudGVyMg==" /var/log/kubernetes/audit.log | tail -1' \
  | python3 -c "
import json,sys,base64
e=json.load(sys.stdin)
print('level  :', e['level'])
print('data   :', e['responseObject']['data'])
print('decoded:', base64.b64decode(e['responseObject']['data']['password']).decode())
"
```

```
1
level  : RequestResponse
data   : {'password': 'aHVudGVyMg=='}
decoded: hunter2
```

**The password is in the audit log.** Act VII found one password in three places. Lesson 06 spent a whole lesson closing the first of them, discovered that the fix does not reach backups, compacted etcd to prove the plaintext was gone — and one line of audit policy has just written it to a plaintext file on the same node, `-rw-------`, destined for whatever log pipeline the organisation runs, where it will be indexed, replicated, and retained under a policy written by a different team for a different purpose.

That is a **fourth location**, and it is worth noticing that it was created by a security control. Not a mistake, not a misconfiguration — a monitoring improvement, requested by an auditor, implemented correctly.

So put it back, and keep the rule that was there for a reason:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/audit/policy.yaml' <<'EOF'
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: [RequestReceived]
rules:
  - level: None
    users: ["system:kube-scheduler", "system:kube-controller-manager", "system:apiserver"]
  - level: None
    resources:
    - group: ""
      resources: ["events"]
  - level: Metadata
    resources:
    - group: ""
      resources: ["secrets", "configmaps"]
  - level: Request
    verbs: ["create", "update", "patch", "delete"]
  - level: Metadata
EOF
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
```

The general rule, and it applies to every logging decision you will ever make: **the audit log inherits the sensitivity of the most sensitive thing you let it record, and it does not inherit the protections.** etcd got encryption at rest and RBAC in front of it. The log file got a `umask`.

### The authorised write that nothing refuses

Now lesson 09's cliffhanger, reproduced with a control from this act. Turn off Pod Security on a namespace — a `PATCH` on a label, by an authorised principal:

```bash
kubectl label ns seen pod-security.kubernetes.io/enforce=privileged --overwrite
sleep 4
docker exec netlab-control-plane sh -c 'grep "\"name\":\"seen\"" /var/log/kubernetes/audit.log' \
 | python3 -c "
import json,sys
for line in sys.stdin:
    e=json.loads(line)
    if e['verb']=='patch':
        print('verb    :', e['verb'], '| level:', e['level'], '| code:', e['responseStatus']['code'])
        print('user    :', e['user']['username'], '| from', e['sourceIPs'])
        print('decision:', e['annotations'].get('authorization.k8s.io/decision'))
        print('body    :', json.dumps(e.get('requestObject')))
        print()
"
```

```
verb    : patch | level: Request | code: 200
user    : kubernetes-admin | from ['172.19.0.1']
decision: allow
body    : {"metadata": {"labels": {"pod-security.kubernetes.io/enforce": "privileged"}}}
```

`code: 200`. `decision: allow`. Nothing refused it and nothing should have — it is a legitimate request by a principal holding the permission. Lesson 03's control has been switched off, and there is no error anywhere in the cluster, no event, no condition, no degraded status. The namespace looks exactly as healthy as it did a minute ago and is no longer protected.

And now look at *which field* saved you: `requestObject`. Because that rule said `level: Request` for writes, the log contains the value the label was set **to**. At `Metadata` you would know that someone patched a namespace, and not what they changed it to — which is the difference between an audit trail and a rumour.

That is the trade this lesson turns on, and it is not resolvable by picking a single level:

| | `Metadata` | `Request` | `RequestResponse` |
|---|---|---|---|
| who did it | ✓ | ✓ | ✓ |
| what they changed it **to** | ✗ | ✓ | ✓ |
| what the object **was** | ✗ | ✗ | ✓ |
| leaks Secrets | no | on write | **on read** |

The workable shape is the policy you now have: `Request` for writes, so you can reconstruct changes; `Metadata` for Secrets, so you cannot reconstruct their contents; and `None` for the noise. Every real audit policy is a version of that, and every one of them is somebody's judgement about which questions they expect to be asked.

### Prediction (c): a policy is mostly about not logging

```bash
before=$(docker exec netlab-control-plane sh -c 'wc -l < /var/log/kubernetes/audit.log')
sleep 60
after=$(docker exec netlab-control-plane sh -c 'wc -l < /var/log/kubernetes/audit.log')
echo "tuned policy, idle cluster: $((after-before)) events in 60s"
docker exec netlab-control-plane sh -c 'tail -400 /var/log/kubernetes/audit.log' | python3 -c "
import json,sys,collections
u=collections.Counter(); r=collections.Counter()
for line in sys.stdin:
    try: e=json.loads(line)
    except: continue
    u[e['user']['username']]+=1
    r[(e.get('objectRef') or {}).get('resource','(non-resource URL)')]+=1
for k,n in u.most_common(5): print(f'  {n:5d}  {k}')
print('  -- resources --')
for k,n in r.most_common(5): print(f'  {n:5d}  {k}')
"
```

```
tuned policy, idle cluster: 149 events in 60s
    109  system:node:netlab-control-plane
     91  system:anonymous
     68  system:node:netlab-worker
     39  system:serviceaccount:kube-system:kindnet
     27  system:serviceaccount:kube-system:kube-proxy
  -- resources --
    110  (non-resource URL)
     77  pods
     46  configmaps
     27  services
     25  leases
```

149 events a minute — about 215,000 a day — on a cluster where **nobody is doing anything**. Two nodes, no workloads of consequence, and every one of those events is Kubernetes talking to itself: kubelets reporting status, controllers renewing leases, `kube-proxy` watching Services.

And second on that list, at 91 of the last 400 events, is `system:anonymous`. Those are the health probes, and lesson 07 taught you both halves of why: `--anonymous-auth=true` is the default, it reaches `/healthz`, `/livez` and `/readyz` and nothing else, and lesson 07 concluded that this is *correct* because "nobody" is a name and what nobody may do is written in ordinary rules. Here is the part lesson 07 could not show you: that correct, harmless default is the second-loudest thing in your audit log, and in a SIEM that alerts on anonymous access it is the reason nobody reads the alerts.

Now measure what the policy is buying. Replace it with the naive version — one catch-all rule, no `None`, no `omitStages`:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/audit/policy.yaml' <<'EOF'
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
EOF
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
sleep 5
before=$(docker exec netlab-control-plane sh -c 'wc -l < /var/log/kubernetes/audit.log')
sleep 60
after=$(docker exec netlab-control-plane sh -c 'wc -l < /var/log/kubernetes/audit.log')
echo "naive policy, same idle cluster: $((after-before)) events in 60s"
docker exec netlab-control-plane sh -c 'du -h /var/log/kubernetes/audit.log'
```

```
naive policy, same idle cluster: 887 events in 60s
2.0M	/var/log/kubernetes/audit.log
```

**887 versus 149.** The tuned policy discards 83% of events on an idle cluster, and the naive one is on course for about 1.3 million events a day describing nothing. Put the good policy back before continuing.

Which inverts how the file reads. An audit policy looks like a list of things to record; it is mostly **a list of things not to record**, and the security-relevant rules are a handful of lines at the bottom of a file whose bulk exists to keep the signal findable. Lesson 07 said a scanner tells you what it checked rather than what is true. An audit log is the opposite failure: it tells you *everything*, which is the same as telling you nothing, until somebody decides what to throw away.

### Prediction (d): where the log stops

```bash
kubectl run target -n seen --image=busybox:1.36 --restart=Never --command -- sh -c 'sleep 3600'
kubectl wait --for=condition=Ready pod/target -n seen --timeout=120s

# (1) the command passed as arguments
kubectl exec -n seen target -- sh -c 'cat /etc/shadow | head -1'
# (2) the same commands typed into a shell
printf 'cat /etc/shadow | head -1\nid\nexit\n' | kubectl exec -i -n seen target -- sh
sleep 4

docker exec netlab-control-plane sh -c 'grep "target/exec" /var/log/kubernetes/audit.log | tail -3' \
 | python3 -c "
import json,sys,urllib.parse
for line in sys.stdin:
    e=json.loads(line)
    print(e['stage'], '| verb:', e['verb'], '| code:', e['responseStatus']['code'])
    print('   ', urllib.parse.unquote(e['requestURI']))
"
```

```
ResponseComplete | verb: get | code: 101
    /api/v1/namespaces/seen/pods/target/exec?command=sh&command=-c&command=cat /etc/shadow | head -1&container=target&stderr=true&stdout=true
ResponseStarted | verb: get | code: 101
    /api/v1/namespaces/seen/pods/target/exec?command=sh&container=target&stderr=true&stdin=true&stdout=true
ResponseComplete | verb: get | code: 101
    /api/v1/namespaces/seen/pods/target/exec?command=sh&container=target&stderr=true&stdin=true&stdout=true
```

The first `exec` is fully legible — `command=sh&command=-c&command=cat /etc/shadow | head -1` — because `kubectl` puts the arguments in the **query string**, and the query string is part of the URI, and the URI is in the log at `Metadata` level.

The second one says `command=sh`. That is all it will ever say. Two commands ran inside that shell and neither appears anywhere.

And the mechanism is right there in the entry: **`code: 101`**. Switching Protocols. The API server upgraded the connection and became a byte pipe between your terminal and a process on a node; from that moment it is not parsing requests, so there are no requests to log. The audit log does not lose track of the commands — it correctly records the last moment at which it could see anything.

Which is the clean statement of what an audit log is, and its limit: **it is a record of requests to the API server, and nothing else is a request to the API server.** Not a process starting inside a container. Not a file being read. Not lesson 09's `tcpdump`, which never touched the API at all. Everything this act taught you about the kernel — capabilities, seccomp, syscalls, the whole `CREATE` and `RUN` end of the timeline — happens somewhere the audit log cannot reach.

### The other sensor

That gap is what runtime detection is for, and it sits at the far right of the act's timeline: **after**. It refuses nothing; it watches syscalls and says what it saw.

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --version 9.1.0 --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf --set tty=true --set falcosidekick.enabled=false
kubectl -n falco rollout status ds/falco --timeout=400s
kubectl logs -n falco ds/falco -c falco | grep -i "Loaded event sources"
```

```
daemon set "falco" successfully rolled out
Loaded event sources: syscall
```

`driver.kind=modern_ebpf` is the choice worth understanding. Falco needs to observe every syscall on the node, and it has historically done that with a kernel module you compile against your running kernel — which is exactly as fragile as it sounds. The modern driver is a **CO-RE eBPF** program: it relies on `/sys/kernel/btf/vmlinux`, the kernel's own description of its own data structures, so one binary works across kernels. And this is a promise being paid. Act I introduced `strace`, measured that it works by *stopping* the program at every syscall, and named eBPF as the near-free alternative — then explicitly declined to use it, on the grounds that a program loaded into the kernel only makes sense once you understand kernel hooks: *"we earn it in the Kubernetes stage, not here."* This is that stage, and `Loaded event sources: syscall` is the thing Act I deferred, declaring what it is attached to.

Be precise about what that line is and is not, because it is easy to over-read. You are watching somebody *else's* eBPF program being loaded, and the log line is that program naming its attachment point. You are not writing one. The half this course does not pay is authoring your own probe — `bpftrace -e 'tracepoint:syscalls:sys_enter_openat { ... }'` and the rest of that world — and it is deliberately out of scope: it needs the map, the verifier and the relocation model, which is a book rather than a lesson. What you *should* be able to do from here is the thing the exams and the on-call pager actually ask: know that the sensor is a kernel program, know that `modern_ebpf` means it relies on the kernel's own BTF rather than a compiled-in module, and know how to check it attached at all instead of assuming. That last one is the whole reason the `grep` above is in the command block and not in the prose.

Now repeat the act the audit log could not see:

```bash
printf 'cat /etc/shadow | head -1\nid\nexit\n' | kubectl exec -i -n seen target -- sh
sleep 8
kubectl logs -n falco ds/falco -c falco --since=60s | grep -iE "Warning|Critical" | head -3
```

```
02:39:15.579192768: Warning Sensitive file opened for reading by non-trusted program |
  file=/etc/shadow evt_type=openat user=root user_uid=0 user_loginuid=-1
  process=cat proc_exepath=/bin/cat parent=sh command=cat /etc/shadow terminal=0
  container_id=0f124d22816f container_name=<NA> container_image_repository=<NA>
  container_image_tag=<NA> k8s_pod_name=<NA> k8s_ns_name=<NA>
```

`command=cat /etc/shadow`. The exact string the audit log did not have, with the syscall that did it (`openat`), the binary (`/bin/cat`), and its parent (`sh`). No rule was written; that is one of Falco's defaults, and it is a **predicate over syscall fields** — which is the same shape as lesson 02's seccomp filter, pointed at the same events, with the verdict changed from `EPERM` to a line of text.

That comparison is the whole argument for having it. A seccomp profile that blocks `openat` on `/etc/shadow` cannot be written, because lesson 02 measured why: in `openat` the path is a pointer into the caller's memory, which is why AppArmor exists and seccomp cannot do paths. Falco reads the same syscall *after* it has happened, when the path is knowable. Refusing requires deciding before; describing only requires being there.

### Neither sensor knows what the other knows

Read the end of that alert again, because it is the finding that matters:

```
container_name=<NA>  k8s_pod_name=<NA>  k8s_ns_name=<NA>
```

Falco saw the syscall and **could not name the Pod.** It is a process on a node watching a kernel; Kubernetes identity is not something the kernel knows, so it has to be enriched from the container runtime and the API server, and here that enrichment produced nothing. What you get is a container ID:

```bash
kubectl get pod target -n seen -o jsonpath='{.status.containerStatuses[0].containerID}{"\n"}'
```

```
containerd://0f124d22816ffa9b27ab187d1e379424d4ccb534a03bba4583379bc9aa3a313b
```

The `0f124d22816f` in the alert is the first twelve characters. So the answer is recoverable — by joining on a truncated ID against every container in the cluster, at the moment of the incident, before that Pod is deleted and the mapping ceases to exist.

Which gives the lesson its point, and it is a symmetry rather than a list of features:

| | knows | cannot see |
|---|---|---|
| **audit log** | the Kubernetes identity — user, group, credential, RBAC grant, object, verdict | anything that is not an API request: syscalls, files, processes, packets |
| **Falco** | the syscall, the process, the arguments, the file | which Pod, namespace, or user — unless enrichment works |

**The audit log knows who and not what. The runtime sensor knows what and not who.** An incident is a sentence containing both, which is why every real investigation is a join, why the container ID and the timestamp are the load-bearing fields in both records, and why "we have audit logging" and "we have runtime detection" are each half of one control.

It also explains the shape of the products. Everything sold in this space is a correlation engine with two sensors bolted to it, and its actual value is the join — which is worth knowing when you are deciding whether to buy one or write the `grep`.

### What the detector costs

One more thing to look at, because lesson 07 taught you to ask it about kube-bench:

```bash
kubectl get ds falco -n falco -o json | python3 -c "
import json,sys
d=json.load(sys.stdin)['spec']['template']['spec']
for c in d['containers']:
    print(f\"  {c['name']:<24} privileged={(c.get('securityContext') or {}).get('privileged')}\")
print('  hostPaths:', [v['hostPath']['path'] for v in d['volumes'] if 'hostPath' in v])
"
```

```
  falco                    privileged=True
  falcoctl-artifact-install privileged=None
  falcoctl-artifact-follow  privileged=None
  hostPaths: ['/var/run/docker.sock', '/run/podman/podman.sock',
  '/run/host-containerd/containerd.sock', '/run/containerd/containerd.sock',
  '/run/crio/crio.sock', '/run/k3s/containerd/containerd.sock',
  '/boot', '/lib/modules', '/usr', '/etc', '/sys/kernel', '/proc']
```

`privileged: true`, and twelve host paths including `/proc`, `/etc`, `/usr`, and **every container runtime socket on the machine**.

Lesson 01 measured what `privileged: true` is: 41 of 41 capabilities, a writable `/proc/sys`, and `/dev` going from 16 to 170 entries. Lesson 03 measured that `baseline` refuses both `privileged` and `hostPath`. And a mounted container runtime socket is the single most direct escape primitive there is — anything that can talk to `/var/run/docker.sock` can start a privileged container on the host.

So the detector that watches for container escapes is deployed with everything a container escape wants, on every node, and **the policies you spent lessons 01 through 03 building would refuse it.** Lesson 07 found this with kube-bench and called it "a scanner needs back most of what this act took away". Here it is sharper, because this one is permanent rather than a job that runs and exits.

This is not an argument against running it. It is the honest accounting: **observability is privileged by construction**, since seeing everything requires being allowed to see everything. The mitigation is not to relax the policy but to treat the exemption as a named, reviewed decision — a `PolicyException` or an `exemptions.usernames` entry from lesson 03's `AdmissionConfiguration`, scoped to that one ServiceAccount in that one namespace, with somebody's name on it. An exemption that exists deliberately is a control. An exemption that exists because the policy was switched off in that namespace to make the DaemonSet start is the thing this act keeps warning you about.

> **Check yourself —** you get an alert: `Sensitive file opened for reading by non-trusted program`, `container_id=0f124d22816f`, `k8s_pod_name=<NA>`, timestamped nine hours ago. You have the audit log and Falco's output. Walk the investigation, and name the point at which it most likely fails.

<details>
<summary>Answer</summary>

**The join, and it fails at the first step more often than anywhere else.**

The only handle is a truncated container ID and a timestamp. To turn that into a Kubernetes identity you need the container-ID-to-Pod mapping *as it was nine hours ago*, and that mapping lives in `status.containerStatuses[].containerID` on a Pod object. If the Pod has been deleted — a rollout, a scale-down, a crash, a completed Job — the object is gone and there is nothing to join against. Nine hours is comfortably long enough. This is the practical reason mature setups enrich at capture time rather than at query time: the identity is only knowable while the workload exists.

If the Pod does still exist, the walk is:

1. **Falco → Pod.** Match the twelve-character prefix against `kubectl get pods -A -o json`. That gives you namespace, Pod, node, ServiceAccount and image.
2. **Pod → who created it.** Search the audit log for a `create` on that Pod name. At `Request` level you get the whole spec, so you can see whether it was a person or a controller, and if a controller, whose Deployment.
3. **Pod → who reached it.** Search the audit log for `pods/exec` on that name around the timestamp. If the alert's `parent=sh` and you find an `exec` with `command=sh` at the same second, you have joined the syscall to a username, a source IP and a client certificate fingerprint.
4. **The blind spot to state out loud.** If step 3 finds an `exec` whose URI is only `command=sh`, the audit log will never tell you what was typed. Falco's alerts *are* the transcript, and only for the actions that happened to match a rule. The commands that matched nothing are gone.
5. **Then widen.** Same credential fingerprint, other requests, same window — that is the `credential-id` field earning its keep, because it distinguishes one certificate from every other one issued to the same user.

**And the thing to check before believing any of it:** whether Falco was running on *every* node at that time, and whether the audit log covers the window at all. Both are DaemonSet-and-retention questions rather than security questions, and both routinely make an investigation impossible. `--audit-log-maxbackup=3` at 100 MB is a few hours on a busy cluster.

The reflex worth keeping: **an alert is a pointer into two logs, and its value is bounded by the shorter retention of the two.**

</details>

<!-- figure -->
```
   NINE LESSONS OF REFUSALS. THESE TWO CONTROLS REFUSE NOTHING.
   because THE INTERESTING FAILURES ARE AUTHORISED. an attacker
   who is using your API is not sending malformed requests.

   PREDICTION (a): grep -c audit  ->  0
     no /var/log/kubernetes. TEN LESSONS OF WORK, UNRECONSTRUCTABLE.
     4 of kube-bench's 11 FAILs (L07) were --audit-log-*: this lesson.
     the default is not negligence: an unbounded file on your control
     plane, and k8s cannot know where you ship it or what you can keep.
     --audit-log-maxsize=100 --maxbackup=3 = 400MB, then GONE.
     that IS the retention policy, on the node it describes.

   THE THIRD THREE-PART EDIT (L03 promised three; this is it)
     and it needs the pattern TWICE: policy = readOnly mount,
     log = WRITABLE mount. flag alone -> crashloop, as ever.
     rules are ORDERED, FIRST MATCH WINS (Act II's iptables chain)
     4 LEVELS = a ladder of how much is kept:
       None < Metadata (who/what/when/verdict) < Request (+ body
       sent) < RequestResponse (+ body returned)
     omitStages: RequestReceived  -> HALVES volume for free.

   ONE ENTRY, READ COMPLETELY -- three payoffs of earlier acts
     hunter2 is NOT in it. Metadata = who read WHICH Secret.
     user.username + groups .... Act IX's authn RESULT, recorded
     extra.credential-id ....... X509SHA256=d6b667f1... THE
       SPECIFIC CERTIFICATE. not "an admin" -- THAT one. Act VIII
       made you compute fingerprints; "rotate the compromised
       credential" REQUIRES KNOWING WHICH ONE.
     authorization.k8s.io/reason:
       "RBAC: allowed by ClusterRoleBinding kubeadm:cluster-admins
        of ClusterRole cluster-admin to Group ..."
       *** THE LOG RECORDS WHICH RULE ALLOWED IT ***
       Act IX's hard direction was "who CAN do X" (enumerate every
       binding). this answers "who DID, and BY WHICH GRANT" for
       free -- the evidence you need to remove a permission safely.

   L03's THIRD VERB, FINALLY READ
     label audit=restricted, create a plain Pod -> "pod/bad created"
     annotation pod-security.../audit-violations = the SAME FOUR
       fields L01+L02 derived by experiment, in full.
     "tells only the audit log" -> and the log is OFF by default,
     so the third verb is useless in a default cluster.
     AND THE QUIET WIN: annotation enforce-policy = privileged:latest
       = the RESOLVED policy for THIS REQUEST, after defaults and
       exemptions. L03 PROVED label-enumeration is unsound in BOTH
       directions. THIS is the sound answer -- but only for
       namespaces somebody recently tried to create a Pod in.

   PREDICTION (b): RequestResponse ON SECRETS
     grep -c aHVudGVyMg==  ->  1
     responseObject.data.password -> hunter2
     Act VII found ONE PASSWORD IN THREE PLACES. L06 spent a whole
     lesson closing #1, found the fix misses backups, compacted etcd
     to prove it. ONE LINE OF AUDIT POLICY CREATES A FOURTH.
     not a mistake -- A MONITORING IMPROVEMENT AN AUDITOR ASKED FOR.
     => THE LOG INHERITS THE SENSITIVITY OF THE MOST SENSITIVE THING
        IT RECORDS, AND NONE OF THE PROTECTIONS. etcd got encryption
        at rest and RBAC. the log file got a umask.

   THE AUTHORISED WRITE (L09's cliffhanger, with L03's control)
     patch ns: enforce=privileged  ->  code 200, decision allow
     nothing refused it and NOTHING SHOULD HAVE. no error, no event,
     no condition. the namespace looks as healthy as a minute ago
     and is no longer protected.
     WHICH FIELD SAVED YOU: requestObject -- only present because
     the rule said level: Request for writes.
       Metadata = "someone patched a namespace"   <- a rumour
       Request  = "...and set enforce=privileged" <- an audit trail
                        Metadata  Request  RequestResponse
       who did it           v        v          v
       changed it TO        x        v          v
       what it WAS          x        x          v
       leaks Secrets       no    on write   ON READ
     the workable shape: Request for writes, Metadata for Secrets,
     None for noise. every real policy is a version of that.

   PREDICTION (c): 149 EVENTS/MIN ON A TOTALLY IDLE CLUSTER
     ~215k/day, all of it Kubernetes talking to itself.
     and SECOND LOUDEST at 91/400: **system:anonymous** -- L07's
     health probes, the default L07 concluded was CORRECT. and it is
     why nobody reads the anonymous-access alerts in a SIEM.
     naive policy (one catch-all Metadata, no None, no omitStages):
       887 EVENTS/MIN  ->  ~1.3M/day describing nothing. 83% DISCARDED.
     => AN AUDIT POLICY LOOKS LIKE A LIST OF THINGS TO RECORD. IT IS
        MOSTLY A LIST OF THINGS NOT TO. L07: a scanner tells you what
        it CHECKED, not what is true. an audit log is the OPPOSITE
        failure -- it tells you EVERYTHING, which is the same as
        nothing, until somebody decides what to throw away.

   PREDICTION (d): WHERE THE LOG STOPS
     exec with args:  ?command=sh&command=-c&command=cat /etc/shadow
                      | head -1        <- FULLY LEGIBLE (query string)
     commands TYPED into a shell: ?command=sh     <- AND THAT IS ALL
       two commands ran. neither appears anywhere.
     THE MECHANISM IS IN THE ENTRY:  code: 101  Switching Protocols.
       the apiserver became A BYTE PIPE. it is no longer parsing
       requests, so there are no requests to log. the log does not
       lose the commands -- IT RECORDS THE LAST MOMENT IT COULD SEE.
     => AN AUDIT LOG IS A RECORD OF REQUESTS TO THE API SERVER, AND
        NOTHING ELSE IS A REQUEST TO THE API SERVER. not a process
        starting, not a file read, not L09's tcpdump. the entire
        CREATE/RUN end of this act's timeline is out of reach.

   THE OTHER SENSOR -- at "AFTER", the far right of the timeline
     driver.kind=modern_ebpf: CO-RE eBPF over /sys/kernel/btf/vmlinux
       (the kernel describing its own structs) -> one binary, many
       kernels, instead of a module compiled per kernel.
       Act I met eBPF as the rescue from strace stopping the world.
     "Loaded event sources: syscall"
     the same invisible act, seen:
       Warning Sensitive file opened ... evt_type=openat process=cat
       proc_exepath=/bin/cat parent=sh command=cat /etc/shadow
     a DEFAULT rule, and it is A PREDICATE OVER SYSCALL FIELDS --
     THE SAME SHAPE AS L02's SECCOMP FILTER, same events, verdict
     changed from EPERM to a line of text.
     AND WHY IT CAN DO WHAT SECCOMP CANNOT: L02 measured that in
     openat the PATH IS A POINTER INTO CALLER MEMORY (hence AppArmor).
     Falco reads the syscall AFTER, when the path is knowable.
     REFUSING requires deciding BEFORE. DESCRIBING only requires
     BEING THERE.

   *** AND NEITHER SENSOR KNOWS WHAT THE OTHER KNOWS ***
     container_name=<NA>  k8s_pod_name=<NA>  k8s_ns_name=<NA>
     it saw the syscall and COULD NOT NAME THE POD -- a process
     watching a kernel; k8s identity is not a thing the kernel knows,
     so it must be ENRICHED, and here enrichment produced nothing.
     all you get: container_id=0f124d22816f
       = the first 12 chars of containerd://0f124d22816ffa9b...
       recoverable ONLY by joining against every container in the
       cluster, AT THE TIME, BEFORE THAT POD IS DELETED.
              KNOWS                        CANNOT SEE
     audit  | user/group/credential/RBAC | syscalls, files,
            | grant/object/verdict       | processes, packets
     Falco  | syscall/process/args/file  | which Pod, ns, or user
     THE AUDIT LOG KNOWS WHO AND NOT WHAT.
     THE RUNTIME SENSOR KNOWS WHAT AND NOT WHO.
     an incident is a sentence containing BOTH -> every real
     investigation is A JOIN, on container ID and timestamp, and its
     value is bounded by THE SHORTER RETENTION OF THE TWO.
     (everything sold in this space is a correlation engine with two
      sensors bolted on. the join IS the product.)

   WHAT THE DETECTOR COSTS (L07 taught you to ask)
     falco: privileged=True + 12 hostPaths incl /proc /etc /usr
       AND EVERY CONTAINER RUNTIME SOCKET (/var/run/docker.sock --
       the most direct escape primitive there is).
     L01: privileged = 41/41 caps, writable /proc/sys, /dev 16->170.
     L03: baseline refuses privileged AND hostPath.
     => THE DETECTOR THAT WATCHES FOR ESCAPES IS DEPLOYED WITH
        EVERYTHING AN ESCAPE WANTS, ON EVERY NODE, AND YOUR OWN
        L01-L03 POLICIES WOULD REFUSE IT. (L07 said a scanner needs
        back most of what this act took away. this one is PERMANENT.)
     not an argument against running it. OBSERVABILITY IS PRIVILEGED
     BY CONSTRUCTION: seeing everything requires being allowed to.
     the fix is not a relaxed policy but a NAMED, REVIEWED exemption
     -- a PolicyException or L03's exemptions.usernames, scoped to
     that one SA in that one namespace, with somebody's name on it.
     an exemption that exists DELIBERATELY is a control. one that
     exists because the policy was switched off to make the DaemonSet
     start is the thing this whole act keeps warning you about.
```

**Cleanup.** Take the detector out first, then the API server flags — and note the log file survives the flag removal, which is the point of the last line:

```bash
helm uninstall falco -n falco
kubectl delete ns falco seen --ignore-not-found

docker exec netlab-control-plane sh -c \
  'cp /root/ka-audit.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
docker exec netlab-control-plane grep -c audit /etc/kubernetes/manifests/kube-apiserver.yaml

docker exec netlab-control-plane sh -c 'ls -l /var/log/kubernetes/audit.log'
docker exec netlab-control-plane rm -rf /etc/kubernetes/audit /var/log/kubernetes /root/ka-audit.bak
rm -f /tmp/ka.yaml
```

That `ls` before the `rm` is the lesson's last measurement. Auditing is off, the flags are gone, and the file — including, if you ran the `RequestResponse` section, a password — is still sitting on the node. Disabling a log does not remove one, and on a real cluster that file has already been shipped somewhere you are not cleaning up.

> **You understand this when you can** say why this act needs a control that refuses nothing, in terms of what an authorised request looks like; check whether a cluster keeps an audit log and explain why "no" is the default rather than an oversight; perform the audit three-part edit and say which of the two mounts must be writable and why; name the four levels in order and say exactly what each adds; explain what `omitStages: RequestReceived` saves and the one case the omitted stage is for; read a single audit entry and identify the field that names the specific credential, the field that names the authorising RBAC rule, and say what question each one answers that Act VIII and Act IX left open; produce a PSA `audit-violations` annotation and say why lesson 03 could not show it to you; explain why the `enforce-policy` annotation is a sound answer to a question lesson 03 proved label enumeration cannot answer, and state its one limitation; demonstrate that `RequestResponse` on Secrets writes a password to disk, connect it to the three locations Act VII found and the one lesson 06 closed, and state the general rule about a log's sensitivity versus its protections; fill in the three-way table of what each level can and cannot reconstruct, and defend a policy that mixes them; demonstrate an authorised write that disables a control, say what the cluster shows afterwards, and name the field that makes it investigable; measure the event rate of an idle cluster, explain what dominates it, identify which of lesson 07's correct defaults is the second-loudest source, and say what that does to an alerting pipeline; compare a tuned and a naive policy and state what an audit policy mostly is; predict and explain which parts of a `kubectl exec` reach the log, quote the status code that explains the boundary, and give the one-sentence definition of an audit log's scope that follows; say what CO-RE eBPF relies on and why it replaced a per-kernel module; explain why a runtime rule can match on a file path when lesson 02 proved seccomp cannot, in terms of when each one runs; state the two blind spots as a symmetry and say what that implies about incident investigation, which two fields the join uses, and what bounds its value; and account honestly for what the detector itself requires, naming which of your own earlier policies would refuse it and what the correct response to that is.

**Which raises:** this lesson made one password worse. Act VII found it in three places, lesson 06 closed the first and could not touch the other two, and a single line of audit policy created a fourth — in a file that outlives the flag that made it. Follow that pattern back and something is obviously wrong: the password has now leaked into etcd, a node's memory, a process environment, and a log, and every one of those is a *consequence of the cluster holding the authoritative copy*. Every fix so far has been an attempt to defend a copy that should not have been there. **So what would it look like for the cluster to never hold the real secret at all — and given that a Pod still has to end up with a password in its environment or a file, what exactly would that buy you?**

---

↑ **[Act X overview](README.md)** · Prev: **[Encryption between Pods](09-encryption-between-pods.md)** · Next: **[Secrets from outside the cluster](11-secrets-from-outside.md)** →
