# The lab for Act V — a real cluster on your laptop with kind

Acts I through IV run inside one netshoot container. Act V needs something the single container cannot give you: real nodes, a real kube-proxy writing real iptables chains, a real CoreDNS, real Pods with their own namespaces on more than one machine.

You do not need a cloud account or a spare server for this. You need **kind** — "Kubernetes IN Docker" — which builds a genuine cluster where each *node* is itself a Docker container.

That is the whole trick, and it is a beautiful one: because a kind node is a container, you can `docker exec` straight into it and run every node-level command in this act — read the `KUBE-SERVICES` chains, watch `conntrack`, list the veth pairs, run `ip route` — against a cluster that is otherwise the real thing. A node you can open a shell into is a node you can understand.

This is also the *right* way to do Act V on a Mac. The `--network host` flag from the orientation lab does not behave on Docker Desktop the way it does on Linux, because Docker Desktop runs everything inside a hidden Linux VM and "host" means the VM, not your Mac. kind sidesteps that entirely: the cluster lives in Linux containers, and you inspect it by exec-ing into those Linux containers, so the kernel you are reading is a real Linux kernel doing real Kubernetes networking.

## Install and create a two-node cluster

You run these in your own terminal (not inside netshoot), and you can run them from **any folder you like** — Act V needs no files from the course at all, since every manifest in it is written out by the lesson that uses it. First, the prerequisites — **Docker must be installed and running** (see [the orientation](../00-orientation/README.md) if it isn't yet), and you need `kind` and `kubectl`. Confirm and install:

```bash
docker info >/dev/null 2>&1 && echo "Docker is up" || echo "start Docker Desktop first"
brew install kind kubectl          # Homebrew — see brew.sh if you don't have it
kubectl version --client           # 1.30 or newer; one drill in this act needs it
```

A single-node cluster is enough for Services, CoreDNS, and iptables. But the most illuminating experiments in this act are about packets crossing *between* nodes — that is the entire point of the CNI and overlay material — so create two nodes. Two extra details in the config below buy you the [Ingress](06-ingress.md) lesson for free later: the control-plane node gets the label `ingress-ready=true`, and host ports 80 and 443 are mapped into it. Drop the config into a file (this writes `kind-2node.yaml` in your current folder):

```bash
cat > kind-2node.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
  - role: worker
EOF
```

Then build the cluster (this takes a minute the first time, while it pulls the node image). Note the `--image` flag — you are pinning the Kubernetes version rather than accepting a default, and the next paragraph is why:

```bash
kind create cluster --name netlab --config kind-2node.yaml --image kindest/node:v1.36.1
kubectl get nodes -o wide          # netlab-control-plane and netlab-worker, each with an internal IP
docker ps --filter name=netlab     # the same two nodes, as Docker containers
```

**Why pin, when the tempting thing is to leave it off.** Without `--image`, `kind` installs whichever Kubernetes *its own* release pinned, so your cluster's version becomes a fact about the day you installed `kind` rather than anything you chose. That costs you nothing in this act and quite a lot later, because three things downstream have a version *floor*:

| what needs it | floor | why |
|---|---|---|
| [Act VI drill 5](../act-6-control-plane/diagnose.md) | **server 1.29** | it deletes `clusterrolebinding kubeadm:cluster-admins` and recovers through `/etc/kubernetes/super-admin.conf`. Neither of those existed before 1.29, so on an older node image the drill's own reproduce step fails `NotFound` and there is nothing to diagnose |
| [Act X lesson 04](../act-10-cluster-security/04-deciding-before-it-exists.md), final section | **server 1.36** | `MutatingAdmissionPolicy` reached `admissionregistration.k8s.io/v1` there |
| [Act V drill 4](diagnose.md) | **`kubectl` 1.30** | `kubectl debug node/… --profile=sysadmin`. This one is your *client*, not the node image — `kubectl version --client` tells you, and `brew upgrade kubectl` fixes it |

So any tag at `v1.36` or above satisfies every server-side floor in the course, and `v1.36.1` is the version every recorded output in Acts VI through X was captured on. If that tag has aged out by the time you read this, take the newest one from [kind's release notes](https://github.com/kubernetes-sigs/kind/releases) and use it everywhere below — the floor is what matters, not the exact patch.

That second-to-last line shows nodes; the last line shows that those nodes *are* containers. The defaults match the example addresses used throughout this act almost exactly: the service CIDR is `10.96.0.0/16` (so the `kubernetes` Service is `10.96.0.1` and CoreDNS is `10.96.0.10`), and the Pod CIDR is `10.244.0.0/16`. The IPs in [Services and kube-proxy](03-services.md) and [CoreDNS](04-coredns.md) will look familiar because kind uses the same conventional ranges.

## When cluster creation fails — the recovery path

`kind create cluster` either works in about a minute or fails in one of four recognizable ways. None of them is mysterious once you know which one you have, and each has a specific move.

**It hangs on "Ensuring node image".** kind is pulling a node image of roughly a gigabyte, and a slow or blocked connection looks identical to a hang. Pull the image yourself first, where you can see progress, then create the cluster — with the image already local, creation skips the download:

```bash
docker pull kindest/node:v1.36.1
kind create cluster --name netlab --config kind-2node.yaml --image kindest/node:v1.36.1
```

Use the same tag in both commands, and the same tag you pinned above. A mismatch means kind pulls a *different* image and you wait all over again — and if the tag you reach for here is older than `v1.36`, you have quietly built the cluster that fails Act X's lesson 04 and Act VI's fifth drill.

**It fails on a port that is already taken.** The `extraPortMappings` above ask Docker for host ports 80 and 443. If something on your Mac already holds one — another kind cluster, a local web server, an old container — creation fails with a bind error naming the port. Find the holder and stop it, or drop the two mappings from the config and skip the Ingress lesson's `curl`s:

```bash
kind get clusters                                  # an older cluster still holding the ports?
docker ps --filter publish=80 --filter publish=443 # a container holding them
```

**It fails, or a node never leaves `NotReady`, on too little memory.** Each node is a full container running a kubelet and a container runtime; a two-node cluster wants **at least 4 GB** given to Docker Desktop, and Docker Desktop's default is often less. Check what it has, and raise it in *Docker Desktop → Settings → Resources* if it is short:

```bash
docker info --format '{{.MemTotal}}'   # bytes available to the Docker VM; want ≳ 4e9
kubectl get nodes                      # NotReady on both nodes right after create = starved
```

**A node sits at `NotReady` with plenty of memory.** `NotReady` is the kubelet saying "I have no working Pod network," so read the node's own reason rather than guessing:

```bash
kubectl describe node netlab-worker | grep -A5 Conditions
kubectl get pods -n kube-system -o wide     # CNI and CoreDNS Pods: are they Running?
```

The overwhelmingly common cause is that the CNI has not started — which is *expected and permanent* on the `disableDefaultCNI` cluster below until you install one. CoreDNS also stays `Pending` until a CNI exists, because CoreDNS is a Pod and a Pod needs a network. That is not a broken cluster; that is a cluster politely waiting for the thing this act is about.

When any of these leaves you with a half-built cluster, delete it before retrying — a partially created cluster keeps its node containers and its ports:

```bash
kind delete cluster --name netlab
```

## The two ways in: node-level and Pod-level

Every command in this act runs from one of two vantage points, and kind gives you both.

For **node-level** commands — the iptables chains, the routing table, the bridge, conntrack — open a shell in the node container. The kind node image ships with `iptables` and `ip`, which covers the [Services](03-services.md) and [CNI](05-cni.md) experiments directly:

```bash
docker exec -it netlab-control-plane bash
# now you are root inside the node:
iptables -t nat -L KUBE-SERVICES -n | head
ip route                              # one route per Pod subnet — the CNI's work
```

The node image does **not** ship `tcpdump`, `ss`, `dig`, or `conntrack`. When you need those at the node level, attach netshoot to the node's namespaces with `kubectl debug`, whose `sysadmin` profile gives you the privilege to read conntrack and capture packets:

```bash
kubectl debug node/netlab-control-plane -it --profile=sysadmin --image=nicolaka/netshoot
# this Pod shares the node's network namespace — its tcpdump sees the node's traffic:
conntrack -L | grep 10.96            # the live ClusterIP → Pod NAT mappings (Services lesson)
tcpdump -i any -nn udp port 8472     # overlay traffic, if your CNI uses VXLAN (see note below)
```

For **Pod-level** commands — DNS resolution, reachability between Pods, `ss` inside a destination Pod — run netshoot as an ordinary Pod and you are exactly where a real application would be standing:

```bash
kubectl run net --rm -it --image=nicolaka/netshoot -- bash
# inside the Pod:
cat /etc/resolv.conf                                       # the kubelet-written resolver
dig kubernetes.default.svc.cluster.local                  # one A record: the ClusterIP
```

This Pod is the perfect place to run the entire five-question debugging method from [The debugging method](08-debugging.md), because it has every tool and it sits in the same position as the broken application you are diagnosing.

## Mapping each Act V file to a command you can run now

Every lesson in the act has a foothold on this cluster. This is the map from lesson to first command.

| Lesson | Run this to make it real |
|---|---|
| [The Pod](02-pod-networking.md) | Deploy anything (`kubectl create deployment web --image=nginx --replicas=2`), then `docker exec` into the node and run `crictl ps` to find the `pause` containers — one per Pod — and confirm with `ls -la /proc/<pid>/ns/net` that every container in a Pod shares one namespace inode. |
| [Services and kube-proxy](03-services.md) | `kubectl expose deployment web --port=80` creates a ClusterIP; prove from a netshoot Pod that the IP appears in no `ip addr` yet `curl`s fine, then `docker exec` into the node and walk `KUBE-SERVICES → KUBE-SVC → KUBE-SEP`. |
| [CoreDNS](04-coredns.md) | The `resolv.conf` and `dig` experiments run verbatim from the netshoot Pod. |
| [CNI](05-cni.md) | `ip route` inside each node container shows the local Pod subnet as a device route and the *other* node's Pod subnet as a route via that node — the cross-node answer made visible. |
| [Ingress](06-ingress.md) | **The one lesson that needs an extra install.** The `extraPortMappings` and `ingress-ready=true` label in the config above are its prerequisites; the lesson itself installs an ingress controller, two backends, and a self-signed TLS Secret, then `curl`s two hostnames at `127.0.0.1`. |
| [Network Policy](07-network-policy.md) | `nmap` from one netshoot Pod to another before and after `kubectl apply`-ing a NetworkPolicy shows the open ports change — **but only on the policy-enforcing cluster below**, not on a default kind cluster. |
| [The debugging method](08-debugging.md) and its [worked failure](09-debugging-walkthrough.md) | The netshoot Pod above is where all five questions get asked. |
| [Diagnose it](diagnose.md) | Each drill breaks this cluster on purpose and cleans up after itself. |

## One honest caveat: kind's default CNI

kind ships with a deliberately minimal CNI called **kindnet**. It does two things differently from a production cluster, and you should know both. First, it routes between nodes with plain host routes, **not VXLAN**, so the `tcpdump -i any udp port 8472` experiment from [Act IV's overlay lesson](../act-4-one-pretends-many/04-overlay-vxlan.md) will show nothing on a default kind cluster — there is no encapsulation to see, because kind's nodes share a Docker bridge and can route to each other directly. Second, kindnet does **not enforce NetworkPolicy**, so the [Network Policy](07-network-policy.md) before/after `nmap` test will show no change: no error, no effect. Both are features of kind's simplicity, not bugs.

## The second cluster: a real CNI, so VXLAN and policy are observable

To *see* VXLAN or *test* NetworkPolicy you turn kindnet off and install a real plugin yourself. This is the config that makes those two experiments work — the same two nodes, with the default CNI disabled:

```bash
cat > kind-cni.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true          # no kindnet — you install the CNI
  podSubnet: "10.244.0.0/16"       # Flannel's default; keeps this act's example Pod IPs
nodes:
  - role: control-plane
  - role: worker
EOF

kind create cluster --name netcni --config kind-cni.yaml --image kindest/node:v1.36.1
kubectl config current-context   # kind switched you to kind-netcni; kind-netlab is still there
kubectl get nodes                # BOTH NotReady — expected: there is no CNI yet
```

Both nodes come up `NotReady` and CoreDNS stays `Pending`. That is the whole point: you are looking at a cluster with no Pod network, which is the state Kubernetes is in before a CNI plugin exists. Now pick which plugin you want to watch, because they give you different experiments:

```bash
# Flannel — VXLAN encapsulation you can tcpdump on udp/8472. Does NOT enforce NetworkPolicy.
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

kubectl get nodes            # both Ready within a minute — the CNI made them usable
```

For **NetworkPolicy enforcement** you want Calico instead. Calico's manifest install creates its default IP pool of `192.168.0.0/16`, so the cluster's `podSubnet` has to agree with it — change that one line in the config above to `podSubnet: "192.168.0.0/16"` before creating the cluster, and expect Pod IPs that read `192.168.x.y` rather than this act's `10.244.x.y`:

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml
kubectl -n kube-system rollout status ds/calico-node    # wait for a Calico agent on each node
```

(Pin whatever version Calico's own install page currently names; the manifest path is stable, the version in it is not.) Both plugins are also the answer to "which entry did the CNI write?" in [the CNI lesson](05-cni.md) — Flannel points cross-node Pod subnets at a `flannel.1` device, Calico at the remote node itself.

> **Check yourself —** On the `disableDefaultCNI` cluster, both nodes report `NotReady` and CoreDNS is stuck `Pending`. Which one of those is the cause of the other?

<details>
<summary>Answer</summary>

`NotReady` is the cause. The kubelet reports `NotReady` while it has no working Pod network, and CoreDNS is itself an ordinary Pod — it needs an IP, a veth, and a route before it can start, and there is nothing to create them. Installing the CNI fixes both at once, in that order: the nodes go `Ready`, then CoreDNS gets scheduled and runs. This is also why "CoreDNS is Pending" is almost never a DNS problem.

</details>

Switch back with `kubectl config use-context kind-netlab` whenever you want the kindnet cluster again — `kubectl config get-contexts` lists both, and every command in this act runs against whichever one is current. If a lesson's output looks nothing like the text, check that first.

When you are done, `kind delete cluster --name netlab` (and `--name netcni`) removes every node container and you are back to a clean machine — the same throwaway-lab discipline as the netshoot `--rm` flag, one level up.

> **You understand this when you can** create a two-node kind cluster, `docker exec` into a node to read its `KUBE-SERVICES` chain, run a netshoot Pod to `dig` a Service to its ClusterIP, and explain why the default-kindnet cluster shows no VXLAN traffic and no NetworkPolicy enforcement until you swap the CNI — and recover on your own when creation hangs on an image pull, a host port is taken, or a node stays `NotReady`.

---

↑ **[Act V overview](README.md)** · Next: **[The Pod — a shared network namespace](02-pod-networking.md)** →
