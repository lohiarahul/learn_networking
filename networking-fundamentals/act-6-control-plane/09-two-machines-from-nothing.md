# Appendix — Two machines, from nothing

Every cluster in this course arrived in one command. `kind create cluster` and there it was: two nodes,
a control plane, a CNI, a working `kubectl`. Eight lessons then took that cluster apart from the
inside — the static pods, the PKI, the loops, the etcd store — and never once asked who put any of it
there.

That is the last unopened box in the act, and it is a big one. `kind` did about a dozen things to those
machines before the first Pod ever ran, and it did them silently. This lesson does them by hand, on two
machines with nothing installed, and the discipline is the course's own: **every prerequisite is earned
by the failure that happens without it.** Do not read the list of steps first. Break each one, read the
refusal, then fix it.

> ### Read this before you start
>
> **This is the one page in the course that has not been run by its author.** Every other lesson in
> Act VI was executed against a live cluster and corrected against what actually happened, several
> times in places where the cluster contradicted the text. This one could not be: it needs two virtual
> machines and a hypervisor, and the environment this course was written in has neither.
>
> So the outputs below are **expected**, not measured, and they are marked as such throughout. They
> come from `kubeadm`'s own documented behaviour and from reading the configuration of the real
> `kind` cluster the rest of the act runs on — which runs the same `kubeadm` code, on nodes that were
> bootstrapped by it. Where the two disagree, the machine in front of you is right and this page is
> wrong. **If you run it, correct it.** The rest of the course earns its confidence from having been
> measured, and this page has not; you should read every claim on it with that discount applied.

## Why this cannot use `kind`

`kind` runs each "node" as a container on one Linux kernel. That is what makes it cheap and it is also
what makes four CKA competencies unreachable inside it:

- **There is no machine to prepare.** Swap, kernel modules, sysctls and the container runtime are all
  the host's, already correct, and not yours to get wrong.
- **`kubeadm init` has already happened**, before you ever saw a prompt.
- **An in-place upgrade is impossible.** [Lesson 06](06-upgrades-and-version-skew.md) says outright
  that `upgrade apply` and `upgrade node` are *"not for your lab — read them, do not run them"*,
  because a `kind` node's binaries come from its image and cannot be replaced under a running kubelet.
- **There is no second control plane to join**, and no load balancer to put in front of one.

So this appendix is where those four get paid, and it is the only place in the course that needs
machines rather than containers.

## The two machines

Either of these works; pick one and stay in it.

```bash
# lima — the lighter option on macOS, and the one this page is written against
limactl start --name=cp --cpus=2 --memory=2 --vm-type=vz template://ubuntu-24.04
limactl start --name=w1 --cpus=2 --memory=2 --vm-type=vz template://ubuntu-24.04
limactl shell cp        # and, in a second terminal, limactl shell w1
```

```bash
# multipass — fewer moving parts if you already have it
multipass launch --name cp --cpus 2 --memory 2G 24.04
multipass launch --name w1 --cpus 2 --memory 2G 24.04
multipass shell cp
```

Two vCPU is not a suggestion. `kubeadm init` refuses fewer, and the refusal is the first preflight
check you will read.

Note the addresses now, on both machines — you will need `cp`'s for the `join` command:

```bash
ip -4 addr show scope global | grep inet        # Act II's command, on a machine you own
```

## Predict first

Before you type anything else, write down your answers. Every one of them is checkable in the next
twenty minutes, and the ones you get wrong are the ones this lesson is for.

1. A kubelet is a process that starts containers. **Why would it refuse to run at all on a machine
   with swap enabled?** You know what swap does; think about what a memory limit means if pages can
   be paged out. ([Act IV's cgroups lesson](../act-4-one-pretends-many/01b-cgroups.md) has the answer
   in it already.)
2. `br_netfilter` makes bridged traffic traverse iptables. **Which of Act V's mechanisms stops working
   without it, and does it fail loudly or quietly?**
3. The kubelet and containerd each have a setting for which cgroup driver to use.
   **What goes wrong if they disagree — and which of the two notices?**
4. `kubeadm init` finishes and prints a `join` command. **How many nodes are `Ready` at that moment,
   and why?** ([Drill 10](diagnose.md) already made you diagnose this exact state on a cluster that
   had it taken away.)

## Step 1 — swap, earned by the refusal

Do not disable swap. Install `kubeadm` and run the preflight checks on their own:

```bash
# on both machines
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.34/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.34/deb/ /' \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update && sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl        # so an unattended upgrade cannot skew you

# on cp only
sudo kubeadm init phase preflight
```

**Expected** — the preflight, not the init, is what refuses:

```
[preflight] Running pre-flight checks
	[WARNING Swap]: swap is supported for cgroup v2 only; the NodeSwap feature gate of the kubelet is beta but disabled by default
error execution phase preflight: [preflight] Some fatal errors occurred:
	[ERROR CRI]: container runtime is not running
```

Two things worth reading in that. The swap complaint is a **warning**, not an error — since 1.28 swap
is tolerated on cgroup v2 behind a feature gate, so the old flat rule ("Kubernetes requires swap off")
is now a version-dependent claim rather than a law. And the *fatal* error is not about swap at all: it
is the missing container runtime, which is the next step.

Turn swap off anyway, and be able to say why: a `memory.max` limit is a promise about resident pages,
and a kernel that can page a container out satisfies the limit while the workload stalls — the
[cgroups lesson](../act-4-one-pretends-many/01b-cgroups.md)'s point that a limit kills you and a
different limit merely slows you down, one layer further down.

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab            # or it comes back on reboot
```

## Step 2 — the runtime, and the cgroup driver that must match

```bash
# on both machines
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
```

Now **do not** set `SystemdCgroup`. Start containerd and look at what the two sides believe:

```bash
sudo systemctl restart containerd
grep SystemdCgroup /etc/containerd/config.toml
```

**Expected:** `SystemdCgroup = false`. And the kubelet's own default, which the package ships:

```bash
grep -r cgroupDriver /var/lib/kubelet/ /etc/kubernetes/ 2>/dev/null
```

**Expected:** `cgroupDriver: systemd` once `kubeadm` has written its config — because on a
systemd-init machine that is the only correct answer. So the two disagree, and the failure this
produces is the one worth recognising: **containerd creates cgroups in one hierarchy while the kubelet
manages another**, both succeed at what they are doing, and the kubelet's resource accounting reads a
tree nothing is writing to. Pods start and then get killed or throttled for reasons that appear
nowhere, and the kubelet restarts in a loop with `failed to get cgroup stats`.

That is the answer to prediction 3, and note its shape: **neither component notices.** Each one is
correct on its own; the disagreement lives between them, which is the same failure mode as
[Act V drill 2](../act-5-kubernetes/diagnose.md)'s selector and label — two strings a human meant to
be the same.

```bash
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
```

## Step 3 — `br_netfilter`, earned by a silence

Skip this and `kubeadm init` will succeed. That is the point.

```bash
# on both machines
cat <<'EOF' | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay && sudo modprobe br_netfilter
cat <<'EOF' | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
```

Three settings, and each one is an Act IV mechanism you have already used:

- **`net.ipv4.ip_forward`** is the one [Act IV's veth-and-bridge lesson](../act-4-one-pretends-many/02-veth-and-bridge.md)
  made you set by hand before two namespaces could reach each other. A node is a router for its Pods.
- **`bridge-nf-call-iptables`** is what makes traffic crossing a *bridge* visit the iptables chains.
  Without it, packets between two Pods on the same node go straight across the CNI's bridge and never
  see `KUBE-SERVICES` — so **ClusterIP DNAT silently does not happen**, and only for same-node traffic.
  That is the answer to prediction 2, and the answer to "loudly or quietly" is the bad one: a Service
  that works for some pairs of Pods and not others, depending on where the scheduler put them. Compare
  [Act X drill 6](../act-10-cluster-security/diagnose.md), where a *security* property had exactly the
  same non-deterministic shape for exactly the same reason.
- **`overlay`** is the storage driver containerd's snapshotter needs, and is the only one of the three
  that fails loudly.

## Step 4 — `kubeadm init`, and reading what it made

```bash
# on cp only
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

`--pod-network-cidr` is not optional in practice: it is the range the CNI will hand out, and several
CNIs read it from the cluster rather than from their own config. `10.244.0.0/16` is what `kind` uses,
which is why every Pod IP in Act V started `10.244.`.

**Expected output**, abbreviated to the four things worth reading:

```
[certs] Generating "ca" certificate and key
[kubeconfig] Writing "admin.conf" kubeconfig file
[control-plane] Creating static Pod manifest for "kube-apiserver"
[addons] Applied essential addon: CoreDNS
Your Kubernetes control-plane has initialized successfully!

kubeadm join 192.168.64.4:6443 --token abcdef.0123456789abcdef \
	--discovery-token-ca-cert-hash sha256:1a2b3c...
```

Then get a `kubectl`, and note that the file you are copying is the one
[lesson 04](04-the-clusters-own-pki.md) taught you to read:

```bash
mkdir -p ~/.kube && sudo cp /etc/kubernetes/admin.conf ~/.kube/config
sudo chown "$(id -u):$(id -g)" ~/.kube/config
```

Now spend five minutes confirming that this machine is the one the last eight lessons described. Every
one of these commands appeared in an earlier lesson, against a cluster somebody else built:

```bash
ls /etc/kubernetes/manifests/           # lesson 02: the four static pods, on a node you made
sudo kubeadm certs check-expiration     # lesson 04: the PKI, one year old as of a minute ago
kubectl get nodes                       # lesson 07, and prediction 4
```

**Expected:**

```
NAME   STATUS     ROLES           AGE   VERSION
cp     NotReady   control-plane   30s   v1.34.x
```

**`NotReady`, and this is prediction 4's answer.** The API server is up, `kubectl` works, etcd is
serving, and the node will not accept work — because there is no CNI, so the kubelet cannot build a
Pod sandbox with networking. You have already diagnosed this exact state:
[drill 10](diagnose.md) removes the CNI config from a working node and the condition it produces is
`Ready=False`, reason `KubeletNotReady`, message `cni plugin not initialized`. Read it here and
recognise it:

```bash
kubectl describe node cp | grep -A3 'Ready '
```

## Step 5 — a CNI, and the node going Ready

```bash
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
kubectl -n kube-flannel rollout status ds/kube-flannel-ds --timeout=180s
kubectl get nodes                       # Ready, within a few seconds of the DaemonSet landing
```

Flannel rather than Calico here for one reason: it reads `--pod-network-cidr` from the cluster, so
there is no second place to get the range wrong. If you would rather use Calico, Act V's
[CNI lesson](../act-5-kubernetes/05-cni.md) is the one that explains what the file you are applying
actually installs — a binary in `/opt/cni/bin`, a config in `/etc/cni/net.d`, and a DaemonSet to put
them there.

## Step 6 — `join`, and what the two halves of the command are for

```bash
# on w1
sudo kubeadm join 192.168.64.4:6443 --token abcdef.0123456789abcdef \
  --discovery-token-ca-cert-hash sha256:1a2b3c...
```

The token expires in 24 hours; if you lost it, `kubeadm token create --print-join-command` on `cp`
prints the whole line again.

Now the question that matters, and it is [Act VIII](../act-8-trust/README.md)'s: **why are there two
secrets in that command?** They point in opposite directions.

- The **token** authenticates the joining node *to* the cluster. Without it, anybody who can reach
  port 6443 could ask for a signed certificate.
- The **CA cert hash** authenticates the cluster *to* the joining node. The node has to fetch the
  cluster's CA before it can trust anything, and it fetches it over a connection it cannot yet verify.
  The hash is what closes that: pin the fingerprint out of band, compare it to what arrives, and a
  machine-in-the-middle serving its own CA is caught.

That is Act VIII's whole problem — *how do you trust the first key?* — with the answer the course kept
pointing at: you do not derive it, you carry it. It is the same manoeuvre as
[Act X's `caBundle`](../act-10-cluster-security/04-deciding-before-it-exists.md), and the same one as
`--cacert` on every `curl` in Act IX.

```bash
# back on cp
kubectl get nodes -o wide       # two Ready nodes
```

And prove the thing the whole exercise was for — a Pod on one machine reaching a Pod on the other,
which is what `bridge-nf-call-iptables` and the CNI and the routes all exist to make true:

```bash
kubectl create deployment web --image=nginx:1.27-alpine
kubectl expose deployment web --port=80
kubectl scale deployment web --replicas=2
kubectl get pods -o wide                       # one on each node, ideally
kubectl run probe --rm -it --image=busybox:1.36 --restart=Never \
  -- wget -qO- http://web/ | head -1
```

## Step 7 — the in-place upgrade lesson 06 would not let you run

This is the CKA task that `kind` cannot host, and the order is the whole of it. **Control plane
first, workers after**, because [lesson 06](06-upgrades-and-version-skew.md) derived the skew rule
from the fact that no component calls another: a kubelet may be up to three minor versions behind its
API server and never ahead of it.

```bash
# on cp: find out what is available before changing anything
sudo apt-mark unhold kubeadm && sudo apt-get update
sudo apt-get install -y kubeadm=1.35.0-1.1 && sudo apt-mark hold kubeadm
sudo kubeadm upgrade plan
```

`upgrade plan` is the command to run in the exam even when you already know the target, because it
prints the component-by-component table and the *manual* steps it will not do for you.

```bash
sudo kubeadm upgrade apply v1.35.0        # rewrites the static pod manifests, one component at a time
```

Then the kubelet on the same machine — and note that `upgrade apply` did **not** do this. It upgraded
the control plane's static Pods and left the kubelet where it was:

```bash
kubectl drain cp --ignore-daemonsets                      # lesson 07's client-side loop
sudo apt-mark unhold kubelet kubectl
sudo apt-get install -y kubelet=1.35.0-1.1 kubectl=1.35.0-1.1
sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet
kubectl uncordon cp
```

And the worker, where the command is different — `upgrade node`, not `upgrade apply`, because there is
no control plane on this machine to rewrite:

```bash
# from cp
kubectl drain w1 --ignore-daemonsets --delete-emptydir-data

# on w1
sudo apt-mark unhold kubeadm && sudo apt-get update
sudo apt-get install -y kubeadm=1.35.0-1.1 && sudo apt-mark hold kubeadm
sudo kubeadm upgrade node
sudo apt-mark unhold kubelet kubectl
sudo apt-get install -y kubelet=1.35.0-1.1 kubectl=1.35.0-1.1
sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet

# from cp
kubectl uncordon w1
kubectl get nodes                      # both Ready, both at v1.35.0
```

Three details that decide the exam task:

- **`apt-mark hold`** on all three packages, always. Without it an unattended upgrade moves a kubelet
  under you and you find out through a skew failure weeks later.
- **`drain` before the kubelet restart, `uncordon` after.** The restart is short; the drain is what
  makes it not matter. And `drain` is [lesson 07](07-node-maintenance.md)'s client-side loop, so
  Ctrl-C leaves it half-done and nothing knows there was a job.
- **`upgrade apply` on the control plane, `upgrade node` on everything else.** One command name is the
  difference between the task passing and the task doing nothing.

## Step 8 — what a second control plane would need

Do not build this; two machines cannot host a quorum worth having and
[lesson 05](05-etcd-backup-and-restore.md) already showed you why a two-member etcd buys nothing at
all. What is worth doing is reading the one field that makes it possible, and understanding why it has
to be set *before* you need it.

```bash
kubectl -n kube-system get configmap kubeadm-config -o yaml | grep -A2 controlPlaneEndpoint
```

On the cluster you just built this is **empty**, and that is the trap. Every node in the cluster, every
`kubeconfig`, and every certificate SAN currently names `192.168.64.4:6443` — one machine's address. A
second control plane joined to that cluster would be a second API server that nothing points at, and
changing it afterwards means reissuing certificates and rewriting every kubeconfig in the estate.

So `controlPlaneEndpoint` is a DNS name or load-balancer address you set at `init` time:

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 \
  --control-plane-endpoint=k8s.internal:6443 \
  --upload-certs
```

`--upload-certs` puts the CA key material into a Secret with a short TTL so that
`kubeadm join --control-plane --certificate-key <key>` can pick it up — which is the same
trust-the-first-key problem as step 6, solved the same way: a secret carried out of band, expiring
fast.

The general rule, and it is the one to carry: **an address that every certificate and every client
config names is not a runtime setting.** It is a decision made once, at the moment of least
information, and paid for later. `kind` made it for you and never said.

## Where this leaves you

You have now done the one thing the rest of the course could not show you: you built the machine that
Act VI spent eight lessons reading. The static pods in `/etc/kubernetes/manifests` are there because a
`kubeadm init` phase wrote them. The PKI has a birthday you watched. The node was `NotReady` until a
DaemonSet put a binary in `/opt/cni/bin`. And the four prerequisites were not a checklist — each one
was a specific failure you can now recognise from its symptom rather than from its position on a list.

> **You understand this when you can** say which of the four prerequisites fails *quietly* and what its
> symptom looks like weeks later; explain why the `join` command carries two secrets pointing in
> opposite directions; give the order of an upgrade and name the one command that differs between a
> control-plane node and a worker; and say why `controlPlaneEndpoint` cannot be set after the fact.

---

← **[When the control plane breaks](08-when-the-control-plane-breaks.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
