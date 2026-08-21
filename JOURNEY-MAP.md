# The Path

**Where you start:** a single program about to call `write()`, with no idea where the bytes go.
**Where you end:** you can look at any abstraction — a Kubernetes Service, an AWS security group, a
TLS handshake, an IAM policy — and *see the mechanism underneath*, well past what the most respected
certifications (Network+/CCNA, CKA·CKAD·CKS, AWS Advanced Networking, AWS Security) actually test.

**The single thread that never breaks:** *everything is a file, and the only question is how `write()`
on one machine becomes `read()` on another.* The idea grows but keeps its shape — a **file** in the
kernel becomes **an object you `GET`/`APPLY`** in Kubernetes becomes **declarative state you
reconcile** in the cloud.

> ## ⚑ What's built, what's roadmap
>
> This map describes the *whole* journey — Stages 0–9. Not all of it is written yet. Read the map for
> the shape of the destination, but know where the built road currently ends:
>
> | Stages | In the repo as | Status |
> |---|---|---|
> | **0–3** — process → sockets → two machines → the internet | orientation + Acts I–III | ✅ **built & teaching** |
> | **6** — one machine pretends to be many (containers) | Act IV | ✅ **built & teaching** |
> | **7.3** — Kubernetes *networking* (incl. Gateway API, Service shapes) | Act V | ✅ **built & teaching** |
> | **7.1** — the control plane: API server as a filesystem, static pods, the reconciliation loop, cluster PKI, etcd backup/restore, upgrades & version skew, node maintenance, control-plane troubleshooting | Act VI | ✅ **built & teaching** — 8 lessons + all supporting pages, every lesson run against a real cluster |
> | **7.2, 7.4, 7.6–7.8** — workloads, scheduling, storage, config, Helm/Kustomize, CRDs/operators, autoscaling | Act VII | ✅ **built & teaching** — 10 lessons + all supporting pages; lessons 01–07 run against a real cluster and corrected, 08–10 pending verification |
> | **4** — cryptography & trust | *(planned as Act VIII)* | 🔜 **roadmap** |
> | **5** — identity & access | *(planned as Act IX)* | 🔜 **roadmap** |
> | **7.5, 7.9** — CKS security: hardening, etcd encryption, seccomp/AppArmor, admission, supply chain | *(planned as Act X)* | 🔜 **roadmap** |
> | **8** — AWS networking | *(none yet)* | 🔜 **roadmap** |
> | **9** — AWS security | *(none yet)* | 🔜 **roadmap** |
>
> The acts were deliberately sequenced to be self-contained across the gaps — Act III (the internet)
> hands off directly to Act IV (containers), so nothing later leans on the unwritten crypto/identity
> stages. The one loose thread this leaves is TLS: Act III bolts the lock on but never opens it, and
> *opening* it is Stage 4 — noted in `05-tls.md` as a deliberate, still-unwritten cliffhanger. The
> `Toolbelt.md` tool roster likewise lists tools for all nine stages; treat Stages 4/5/8/9 there as a
> shopping list for road not yet paved.
>
> **Read Stage 7 below as the destination, not the delivery.** Act V teaches Kubernetes *networking*
> from first principles — Pods, CNI, Services (including headless, SRV and the traffic-policy shapes),
> CoreDNS, Ingress, Gateway API, NetworkPolicy, and a debugging discipline. Act VI teaches the control
> plane: the API server as a filesystem over etcd, static pods, the reconciliation loop, the cluster's
> own PKI, etcd backup and restore, upgrades and version skew, node maintenance, and a diagnostic walk
> for a control plane that will not answer.
>
> Between them that is a real slice of CKA — most of Cluster Architecture, all of Servicing and
> Networking, and the harder half of Troubleshooting. Act VII closes the rest of it — **workloads,
> scheduling, storage, config, Helm, Kustomize, CRDs and autoscaling** — which between them leave
> **Acts I–VII covering essentially all of CKA.** Still missing: **RBAC and observability**, and nothing
> here teaches CKS at all, **so this is not yet a CKS course.** Every "you can now" line in Stage 7 that reaches past
> those topics is roadmap.
>
> If you came here *for* those exams, read [`exam-prep/`](exam-prep/README.md) first — it maps every
> CKA and CKS competency to the lesson that covers it, and marks honestly the ones nothing covers yet.

## How we learn here — seek, don't receive

This is a journey of inquiry, not a catechism. We never hand you an answer to a question you don't yet
have. There is one test over every paragraph we write: **does this keep your spirit of knowing alive?**
If a passage delivers a verdict before you've felt the problem, it fails — we cut it, or turn it back
into a question.

1. **The question comes before the answer — always.** Each topic begins with a wall *you* hit, not a
   truth we announce. You should *want* the idea before it arrives.
2. **Sit in the pain of ignorance.** When you hit the wall we don't rush the rescue. First you try to
   get past it with what you already have, and feel — honestly — where that falls short. The next tool
   or idea then lands as *relief you earned*, not a gift you were handed.
3. **Earn the winner by trying the rivals.** We never assert "X is best." We put X against the obvious
   alternative — or against no tool at all — and let you feel the difference. (Decode `/proc/net/tcp`
   by hand before `ss`; compare busybox `lsof` to the real one; feel `strace` stop the world before
   eBPF ever rescues you.)
4. **Mechanism before tool.** Read the kernel's own file (`/proc/net/tcp`, `nf_conntrack`, `iptables`)
   before the command that prettifies it. A tool that disagrees with the file is wrong.
5. **Predict, then break.** Commit a guess out loud, run the experiment, let the surprise correct you.
6. **The creed is your conclusion, never our premise.** "Everything is a file" is not doctrine we
   preach on page one — it's the thing you catch yourself saying around the tenth time the kernel hands
   you a file. We let it dawn; we never install it.
7. **Pre-shadow by posing, not answering.** A seed dropped for later carries a *question* forward
   ("ARP trusts any reply — sit with that"), never a packaged solution. The recurring spine-ideas — the
   file, *conntrack*, the reconciliation loop — return as questions you already hold, which is what
   makes the whole thing feel like one river rather than a stack of unrelated subjects.
8. **You leave each stage able to *do* something new** — and feeling the crack that opens the next door.

---

## Stage 0 — The actor: a process and the kernel

*Before any wire, meet the thing that will do the talking, and its only tool.*

A process is an address space, a thread of execution, and — the part that matters here — **a table of
open files**. Two processes can't see each other's memory; the only way they communicate is *through
the kernel*, over channels that look and behave like files. That sentence is the seed of everything.

**You can now:** explain a running program as "an address space holding a table of open files," and
say why all communication has to go through the kernel.
**Which raises:** if everything is a file, what kind of file is a *network connection*?

---

## Stage 1 — One machine: sockets and the kernel's own ledgers

*Open the connection-as-a-file and read the books the kernel keeps about it.*

- A **socket is a file** with an address: `socket()` hands back a file descriptor you `read()` and
  `write()` like any other — so we build a tiny HTTP server from `socket → bind → listen → accept`
  and watch the syscalls.
- **Loopback** (`127.0.0.1`) lets a process talk to itself with no network card involved — the kernel
  short-circuits it — which isolates "the socket machinery" from "the wire."
- A **port** lets one machine hold thousands of sockets at once; the kernel exposes the entire socket
  table as a readable file, **`/proc/net/tcp`**, which we decode by hand (before ever touching `ss`).
- Each connection sitting in that file has a **state**, and a half-open *SYN scan* abuses the very
  handshake that creates it — our first glimpse of how a design casts a security shadow.
- Capstone: turn the question on the `/proc` files themselves. **Inodes** (the real file vs. its name),
  **`mount`** (filesystems grafted into one tree), and **magic symlinks** reveal that a file is an
  *interface* the **VFS** answers by running code, not stored bytes — so `everything is a file` finally
  gets *named* (the creed dawns, never preached), tying `/proc/self/fd` + `/proc/net/tcp` + `/proc/net/dev`
  into one mechanism.

- *(optional side road, off the networking spine)* the container's own `/` is an **`overlay`**
  filesystem — `mount` taken further: read-only shared image layers + a private writable layer,
  copy-on-write, why `--rm`/Pod restarts discard changes, and **volumes** for persistence. Reinforces
  `mount`/VFS; sets up K8s storage (emptyDir, PV/PVC) early. Skippable.

**You can now:** read a row of `/proc/net/tcp` unaided; explain why a process that exhausts its
file descriptors can no longer open a connection; and say what a `/proc` file *is* — a function the
kernel runs on read — down to the inode and the VFS.
**Which raises:** loopback only reaches itself. How do two *separate* machines find each other?

---

## Stage 2 — Two machines: a packet's journey, layer by layer

*We build the layers bottom-up, because each one exists only to fix what the layer below couldn't do.*

- **Link layer.** On a local segment, delivery is by **MAC** address inside Ethernet frames; a switch
  learns who's where. **ARP** discovers the MAC for an IP — and trusts *any* answer, with no
  authentication at all (a shadow that will make us want cryptography). A flat L2 network doesn't
  scale or isolate, which is *why* **VLANs** and segmentation exist.
- **Network layer.** **IP** gives a global address; **subnetting and CIDR** decide what's local versus
  what needs a router — we do the binary math by hand, because every cloud network later is just this.
  The **routing table** picks the next hop. Routes are filled either statically or by **routing
  protocols** — and we meet **BGP** specifically, because it runs the internet *and* later turns out
  to be how AWS Direct Connect and Transit Gateway exchange routes. **DHCP** explains how a host gets
  an address in the first place; **MTU and fragmentation** look like trivia now but will bite us hard
  in overlays and VPNs, so we meet them here.
- **The simplest messengers.** **ICMP** carries reachability and errors (this is how `ping` and
  `traceroute` actually work); **UDP** is the bare, connectionless datagram.
- **Names.** **DNS** turns names into addresses over UDP — resolvers, record types, caching, and the
  full resolution walk — because every later system (cluster DNS, Route 53) is this with extra hats.

**You can now:** trace a name → IP → route → MAC by hand, and subnet a network on paper.
*(Cert ground: the bulk of CompTIA Network+ and CCNA.)*
**Which raises:** IP and UDP can drop, reorder, and forge packets, and hide nothing. How do we get a
stream that's reliable *and* private?

---

## Stage 3 — The internet: reliability, the web, and a locked door

*Turn lossy packets into a dependable conversation, then notice we still have no privacy.*

- The **TCP handshake** and sequence numbers turn unreliable IP into an agreed connection; the
  connection then walks a **state machine** (and `TIME_WAIT` exists to protect you from ghosts of old
  connections).
- **Reliability** comes from acknowledgements, retransmission, and a sliding **window** — and
  **congestion control** (slow-start and friends) is *why* real-world throughput ramps and backs off
  the way it does.
- **conntrack** — the kernel keeping a table of every live flow — is introduced here and flagged
  loudly, because it comes back as a Kubernetes Service, an AWS security group, and a stateful
  firewall. Learn it once, recognise it everywhere.
- **The web's evolution as a motivation chain:** HTTP/1.1's head-of-line blocking motivates HTTP/2's
  multiplexing, whose TCP-level blocking motivates HTTP/3 over QUIC (which rides UDP — now you see why
  Stage 2's "bare datagram" mattered). We also meet **proxies and the L4-vs-L7 load-balancing
  distinction** here, so neither feels new when Kubernetes and AWS lean on them.
- Finally, **TLS** appears as a sealed lock on top of TCP. We use it but don't open it — a deliberate
  cliffhanger.

**You can now:** name every TCP state, explain why throughput behaves as it does, and read an HTTP
exchange end to end.
**Which raises:** what is *inside* that lock — and how can a wire nobody trusts carry a secret at all?

---

## Stage 4 — Trust on an untrusted wire (cryptography)

*Everything so far is forgeable and public. We build the three guarantees from scratch.*

- **Integrity:** a **hash** is a one-way digest where one flipped bit avalanches the output.
- **Authenticity:** an **HMAC** uses a shared key to prove a message wasn't forged.
- **Confidentiality:** **symmetric ciphers** and **AEAD** encrypt *and* authenticate together — and
  we see why a naive mode (ECB, the famous visible-penguin image) is broken.
- **The key-distribution problem** forces **asymmetric crypto**: public/private keys, **Diffie–Hellman
  key exchange**, and *forward secrecy* (why stealing today's key shouldn't decrypt yesterday's
  traffic).
- **Signatures** prove authorship; a **certificate** is a signed public key; a **chain of trust** up
  to a root CA is *why* you believe a stranger's certificate. Real life adds **revocation and
  rotation** (CRL/OCSP, expiry) — the part tutorials skip and outages don't.
- Now we **open Stage 3's lock**: the full **TLS 1.3 handshake** is just all of the above composed in
  order. **mTLS** runs it both ways (this becomes service-mesh identity later). And **artifact
  signing** (Sigstore/cosign) plants the seed for supply-chain security.

**You can now:** narrate every message of a TLS handshake and walk a real certificate chain to a root
you trust, explaining each link.
**Which raises:** crypto proves a message is authentic — but *who* is the principal behind it, and
what are they allowed to do?

---

## Stage 5 — Identity and access (who you are, and what you may do)

*Encryption is not authorization. Separate the two cleanly, because every system conflates them and bleeds.*

- The bedrock distinction: **authentication** (who you are) vs **authorization** (what you may do).
- From **passwords → MFA → tokens**; sessions versus stateless tokens.
- A **JWT** is a signed claims blob (recall Stage 4 — the *signature* is the trust, not the contents).
- **OAuth2** delegates access without sharing your password (the flows, scopes); **OIDC** adds an
  identity layer on top; **SAML** is the enterprise-SSO incumbent; **SASL** is the pluggable auth
  framework you meet in SMTP, LDAP, and Kafka.
- **LDAP/directories** are where identity actually lives; **SCIM** provisions users and groups *before*
  they ever log in.
- Two authorization *models* — **RBAC** and **ABAC** — close the stage, because they are exactly what
  Kubernetes RBAC and AWS IAM implement.

**You can now:** draw the OAuth2/OIDC flow, decode and verify a JWT, and explain provisioning (SCIM)
and attribute-based access (ABAC).
**Which raises:** we can now build, address, secure, and identify a service. How does a system run
*thousands* of them for us — declaratively — and heal itself when they fail?

---

## Stage 6 — One machine pretends to be many (the container substrate)

*Before Kubernetes, learn the kernel features it is assembled from — so the cluster is recognition, not magic.*

- **Namespaces** give a process its own private network, PID, mount, and user views — isolation is the
  atom of a container. **cgroups** cap its CPU and memory (this becomes Pod requests/limits and the
  OOM-killer).
- A **veth pair** is a virtual cable and a **bridge** is a virtual switch — exactly how containers on
  a host talk. **iptables/NAT** publishes a container's port (and is stateful *because of* conntrack —
  Stage 3 returns).
- **Overlay networks** use **VXLAN** to make one virtual network span many hosts — and the **MTU**
  problem from Stage 2 comes back to bite, exactly as promised.
- **Images and the OCI runtime** (union filesystems) explain what a container actually *is*.
- Tied together: **Docker as a product** — `docker0` is that bridge, `-p` is that DNAT rule, a compose
  network is namespaces plus a bridge, the overlay driver is VXLAN.

**You can now:** build container networking by hand and explain every Docker network mode in terms of
kernel primitives.
**Which raises:** one host is a capacity ceiling and a single point of failure. How do we schedule and
connect containers across a whole fleet — declaratively?

---

## Stage 7 — Kubernetes (running a fleet, declaratively) — the deep movement

*The mental model up front: the API server is a virtual filesystem, etcd stores the files, and
controllers reconcile desired state toward actual. Everything below is that one loop, applied.*

**7.1 Architecture & the control loop.** The control plane (api-server, etcd, scheduler,
controller-manager), the kubelet, and the container runtime via CRI. The **reconciliation loop** is
introduced as the engine behind *every* later behaviour. We see how `kubeadm` assembles a cluster and
how to **back up and restore etcd** (the thing that, lost, loses everything).

**7.2 Workloads & scheduling.** A **Pod** is a shared network namespace (recall Stage 6). Pod →
ReplicaSet → Deployment (rolling updates), then StatefulSet, DaemonSet, Job/CronJob. Scheduling makes
requests/limits (recall cgroups), node affinity/anti-affinity, taints/tolerations, and topology spread
concrete; probes (liveness/readiness/startup) keep it healthy.

**7.3 Networking & load balancing** — *the section where continuity matters most:*
- The cluster's one rule — *every Pod is routable, no NAT between Pods* — constrains everything else.
- **CNI** is the contract that wires a Pod's veth on creation (recall Stage 6 — mostly a callback).
- A **Service** is a stable virtual IP; **kube-proxy** implements it with **iptables DNAT + conntrack**
  (recall Stages 3 and 6) — this is L4 load balancing, built from things you already own.
- **Then we feel the pain on purpose:** iptables mode walks its rules linearly, so at thousands of
  Services it gets slow; it's blind above L3/4, so it can't express "allow `GET /books` but deny
  `POST`"; and it load-balances crudely. IPVS mode helps but is still netfilter.
- **So eBPF and Cilium are not a surprise — they're the obvious fix.** Programs run *in the kernel
  datapath*, replacing rule-walks with hash-map lookups, attaching **identity** to traffic, and
  understanding **L7** — with **Hubble** showing every flow. By the time we *configure* Cilium, you
  already know exactly why it's taking over.
- Then the rest sits naturally: NodePort/LoadBalancer and **MetalLB** (bare-metal LB IPs), **CoreDNS**
  (recall Stage 2 DNS), **Ingress → Gateway API** (L7 LB + TLS termination, recall Stage 4),
  **NetworkPolicy** (recall firewalls; default-deny), and a **service mesh** with **mTLS** (recall
  Stage 4) — including *why* a mesh exists (retries, identity, traffic shifting) and sidecar vs
  sidecarless.

**7.4 Config, storage, state.** ConfigMap and Secret — and the deliberately uncomfortable discovery
that a Secret is only base64, which *motivates* real secret management. Then volumes, PV/PVC,
StorageClass, CSI, and dynamic provisioning.

**7.5 Security (CKS-grade).** RBAC (recall Stage 5) and ServiceAccount tokens (recall JWT). Cluster
hardening: API-server and kubelet auth, **etcd encryption at rest**. Workload hardening:
SecurityContext, dropped capabilities, **seccomp**, **AppArmor/SELinux**. **Pod Security Admission**,
then **admission control** via validating/mutating webhooks (**OPA Gatekeeper / Kyverno**).
**Supply-chain security:** image scanning (Trivy), **signing and verifying** images (cosign/Sigstore —
recall Stage 4), SBOMs, and admitting only trusted provenance. **Runtime** detection with **Falco**
(recall syscalls) and **audit logging**. Secrets done properly: ESO, Vault, Sealed Secrets, CSI.

**7.6 Packaging, delivery, and platform.** Helm, Kustomize, CDK8s. **GitOps** (ArgoCD/Flux) is just
the reconciliation loop from 7.1 pointed at a git repo — sync waves, app-of-apps, self-heal.
**CRDs and operators** are that *same loop applied to your own object types* — the heart of extending
Kubernetes — and **Crossplane** uses them to provision cloud infrastructure from a one-line claim,
which is our bridge into AWS.

**7.7 Scaling & resilience.** HPA, VPA, **KEDA** (event-driven, scale-to-zero), Cluster Autoscaler,
PodDisruptionBudgets.

**7.8 Observability.** Metrics (Prometheus/ServiceMonitor), dashboards (Grafana, RED/USE), logs
(Loki), traces (Jaeger/OpenTelemetry) — and the disciplined debugging workflow that ties them together.

**7.9 Multi-tenancy, cost, and DR (production).** Namespaces with ResourceQuota/LimitRange and
default-deny; cost attribution (Kubecost); disaster recovery (Velero); upgrades; and CIS benchmarking
(kube-bench, Polaris).

**You can now** — *from Act V as built (7.3 only)* — explain and debug a cluster's whole network path
from first principles: why a Pod is routable, what a CNI plugin does on creation, why a ClusterIP
exists on no interface, how CoreDNS resolves a Service, where TLS terminates, and how a NetworkPolicy
drops a packet. **Once 7.1–7.9 are written**, you will be able to run, secure, extend and debug a
production cluster end to end. *(Cert ground, when complete: CKA + CKAD + CKS. Act V alone covers the
networking third of it.)*
**Which raises:** all of this runs on infrastructure someone must provision, connect, and defend at
scale — and every primitive there is something you have already built by hand.

---

## Stage 8 — Cloud networking on AWS

*Every AWS networking primitive is a kernel mechanism you already understand, now declarative and at planetary scale.*

- The frame: regions/AZs and the shared-responsibility model.
- **VPC** is your network as software: CIDR planning (recall subnetting), public/private subnets,
  **route tables** (recall the routing table), and the Internet Gateway.
- **Security groups are conntrack** — stateful, which is *why* they need no return rule — versus
  **NACLs**, which are stateless and do (the single most-tested distinction on the exam, and now
  obvious to you). **NAT Gateway** is Stage 6's MASQUERADE; egress-only IGW and IPv6 round it out.
- Connecting networks: **peering**, **Transit Gateway** (hub-and-spoke routing — recall BGP), VPC
  sharing; hybrid via **Site-to-Site VPN** and **Direct Connect** (recall BGP, and the jumbo-frame/MTU
  story from Stage 2). **PrivateLink and VPC endpoints** reach a service without the public internet
  (recall DNS).
- **Route 53**: hosted zones, record types, **routing policies** (weighted/latency/geo/failover),
  health checks, Resolver for hybrid DNS, and DNSSEC.
- **Load balancing**: NLB (L4), ALB (L7), Gateway Load Balancer, target groups, and TLS termination
  with SNI (recall Stage 4) — the same L4/L7 split you met in Stage 3 and used in Stage 7.
- **Edge and global**: CloudFront (why caching at the edge wins), Global Accelerator (anycast), Shield
  (DDoS), and WAF at the edge.
- **Seeing the traffic**: VPC Flow Logs (a conntrack record in the cloud), Traffic Mirroring,
  Reachability Analyzer, CloudWatch.

**You can now:** design and debug a multi-VPC, hybrid, edge-accelerated network by reasoning about the
mechanism rather than guessing in the console.
*(Cert ground: AWS Advanced Networking – Specialty, ANS-C01.)*
**Which raises:** a network you can reach is a network you must defend. Who may touch it, how is data
protected, and how do you know when you're under attack?

---

## Stage 9 — Cloud security on AWS — the capstone

*Defend the whole machine you've built, end to end. Every control here protects something you can already explain.*

- **Identity, deeply.** IAM principals and the full policy family (identity, resource, SCP, permission
  boundaries, session), the evaluation logic, **ABAC** (recall Stage 5), and roles/STS for temporary
  credentials. Then **Organizations and SCPs**, multi-account guardrails, Control Tower, and **IAM
  Identity Center** — federation (recall SAML/OIDC) and provisioning (recall SCIM).
- **Data protection.** **KMS** is envelope encryption — a key encrypting a key (recall symmetric +
  asymmetric) — plus key policies and CloudHSM; **ACM** is managed PKI (recall the chain of trust);
  **Secrets Manager** is KMS + IAM; and encryption at rest across S3/EBS/RDS, with TLS in transit everywhere.
- **Infrastructure protection.** WAF, Shield, **Network Firewall** (stateful — recall conntrack), and a
  disciplined security-group review.
- **Detection and response.** **CloudTrail** is the audit log of every API call; **Config** tracks
  compliance state; **GuardDuty** finds threats across flow/DNS/CloudTrail; **Security Hub** aggregates;
  **Detective** investigates; **Macie** classifies sensitive data; **Inspector** scans for
  vulnerabilities (recall supply chain). Then the **incident-response lifecycle**: contain, eradicate,
  recover, automate.

**You can now:** write least-privilege multi-account policy, design encryption in transit and at rest,
and build a detection-to-response pipeline — because you understand the thing each control defends.
*(Cert ground: AWS Security – Specialty, SCS-C02.)*

**The end goal, reached:** from `write()` to a defended global cloud, you see the mechanism under every
abstraction. That is what it means to be a networking wiz — not memorised flags, but understanding that
goes all the way down.

---

<!-- site:cut -->

*Everything below this line is authoring notes — the tool-selection reasoning and the build order for
whoever writes the next stage. It is kept in the repo on purpose and left out of the published site,
because a reader arriving to see the destination should not land in a backlog.*

## The tool roster — what's in, what we're adding (planning)

*A tool earns its place the same way an idea does: it must make a black box **transparent**, never
hand the reader a new black box to incant. Every tool below is judged against that — does it serve a
**role** in the method (the by-hand mechanism, the earned rival, the lift-the-lid capstone), or is it
just useful? "Useful but role-less" becomes a one-line "in the wild, you'll meet X," not a lesson.*

### Already integrated (current state)

- **Core, load-bearing:** `nc`, `ss`, `ping`, `curl`, `iptables`, `ip route`, **`conntrack`**, `veth`,
  `dig`, `tcpdump`, `nmap`, `lsof`, `ip link`, `drill`, `traceroute`, `strace`, `ip netns`, `ip neigh`,
  `arp`, `nettop`; plus `kind` and `kubectl` for Stage 7.
- **Present but only lightly touched — candidates to *deepen*, not add:** `openssl` (the TLS workhorse —
  Stages 3/4 should lean on `s_client`), `nsenter` (the by-hand mechanism under `kubectl/docker exec` —
  Stage 6), `tshark`, `iperf`, `cilium`, `bpftrace` (each named once).

### Decided in design discussion

- **scapy** — the *active* counterpart to `tcpdump`'s passive read; it lets the reader **become** the
  protocol they've been drawing. Slots:
  - ❌ **Stage 1 (Act 1):** *ruled out by the feedback loop.* Its only Act-1 home (crafting the SYN in
    the SYN-scan) flows uphill — `IP()/TCP()` presupposes the layer model Act 2 builds, and the
    kernel-RST gotcha needs `iptables` (Act 4). Act 1 stays file-pure; nmap remains its scanner.
  - ✅ **Stage 2 (Act 2), DONE:** debuts in the ARP lesson — *"ask for a mapping yourself"*
    (`srp1(Ether()/ARP(op=1,...))`), single-container and verified via the reply + `/proc/net/arp`,
    with `arping` as the earned rival; the gratuitous-ARP forge shown as the same packet, one field
    flipped (described, not run — it's a real LAN). Ladder updated (L1 closer + test-yourself Q10).
  - 🔜 **Stage 3 (Act 3), pending:** handshake + sequence-number forge (the Morris-worm shadow, made
    *doable*) — note the RST-drop needs `iptables`, whose intro lands in Act 4; resolve that seam first.
  - Ships in `netshoot`, zero setup. **Guardrail:** always `.show()` the bytes and *predict the reply*
    before sending — paste-and-run is banking, not seeking.
- 🔜 **level-ip** — *one optional end-of-Stage-3 capstone only.* It opens the single black box the
  file-based method can't reach: the kernel's TCP *code path* (you can read its *state* in `/proc`, never
  its *mechanism*). **Hard-labelled "this is not Linux — read it for the *shape* of the algorithm, then
  go verify the real kernel does the same by experiment."** Heavier setup (clone + `make` + TUN), which
  is exactly why it stays opt-in and never inline.

### Recommended shortlist (open — highest value)

- **Wireshark / tshark** — the **visual rival** to `tcpdump` and a lifelong career tool. Reinforces
  "the file wins": capture with `tcpdump -w`, open the *same* `.pcap` in Wireshark. **Home:** the
  **`in-the-wild.md`** Mac companions (GUI lives where there's a screen); `tshark` for the CLI form.
  - ✅ **Act 2, DONE:** added to Act 2's `in-the-wild.md` as tcpdump's visual rival (capture with the
    built-in `tcpdump -w`, render in Wireshark/`tshark` — the one optional `brew` install on that page).
    Also: `tcpdump` itself is now *earned* on first use in Act 2 L3 (was previously used un-introduced).
  - 🔜 later acts: reach for it again wherever a capture gets too dense to read by eye.
- 🤔 **bpftrace / eBPF** — advanced **lift-the-lid capstone**, sibling to level-ip but a *cleaner* fit:
  it instruments the **real kernel's** functions, not a toy stack — "watch the kernel *think*." Cashes
  out the Cilium/Falco/eBPF seeds already planted in Stages 3 and 7. Opt-in, never paste-blindly.
- 🤔 **Deepen** `openssl s_client` (Stages 3/4 TLS — `nc` for TLS) and `nsenter` (Stage 6 — enter a
  netns by hand before the `exec` abstraction). Both already present; both by-hand mechanism + career tools.

### "In the wild, you'll meet X" one-liners (not full lessons)

- 💡 **`iperf3`** (Stage 2/3 — measure the wire), **`nft`** (Stage 6 — the modern rival to `iptables`),
  **`ethtool`** (Stage 2 — explains the GRO/TSO offload mystery: why `tcpdump` shows a 64 KB "packet" on
  a 1500-MTU link), **Hubble** (Stage 7 — already in the text; the cluster-scale `tcpdump`).

### Explicitly *not* adding

`hping3` (scapy already covers crafting), GUI route inspectors, and any cloud-vendor tooling before
Stages 8–9 — the fundamentals stay vendor-neutral.

### The one failure mode shared by every add

The moment a tool becomes "run my script / read this toy and believe it," it's **banking**, and it
fails the Spirit check. The rule for all of them: **build it / lift the lid, *then* go verify the real
kernel.** Used that way, scapy, Wireshark, bpftrace, and level-ip are all deep expressions of
seek-don't-receive; used as recipes, none of them belong.

---

## Building this path

Build the stages in order; **finish the networking fundamentals (Stages 0–3) first** — they set the
voice and pedagogy every later stage inherits, and everything later is literally built from them.

**The shape of a lesson** follows the method above: (1) hit a wall; (2) try to get past it with what
you already have, and feel the lack; (3) meet the idea as *earned relief*, reading the raw mechanism
first; (4) earn it against a rival; (5) predict, then break; (6) face the shadow it casts (a new
question); (7) name what you can now do, and the question you carry forward.

**The shape of an act:** lessons → `test-yourself` (recall) → a `diagnose.md` of symptom-first **on-call
drills** (transfer). Each drill induces a *real, reproduced* broken state (built from free/stock tools,
never a bespoke artifact — verify it runs on the real kernel before it ships), hands the reader only the
symptom, and hides the diagnosis behind a cover-and-check reveal. Recall tests memory; the drills test
whether they can reach for the right file *unguided* — the actual job.

**The "in the wild" transfer layer:** each act carries its own `in-the-wild.md` (alongside
`test-yourself.md` and `diagnose.md`), reached by a `> On your own machine —` link, which re-runs that
act's idea on the reader's *real Mac* with built-in tools (`lsof`, `arp`, `dig`, `traceroute`,
`networkQuality`, `curl -w`, `tcpdump`). It is transfer, not teaching: a per-act file holds *only* that
act's concepts (so nothing flows uphill — River-safe by construction), and it ends with a **macOS↔Linux
swap section** that aims for a 1:1 translation and, where there isn't one, says *why* in a line and *what
we do instead* (e.g. no `/proc` → `lsof` reconstructs the view; no `ip` → `arp`/`netstat -rn`/`ifconfig`;
`netstat -p` means *protocol*, not process; `networkQuality` is the reverse case — macOS has it, Linux
doesn't).

**Three checks keep us honest.** *River:* nothing may use a concept not yet introduced (no flowing
uphill). *Ladder:* the "you can now" lines must form an unbroken staircase (a gap means a topic is
missing). *Spirit (the one that matters most):* every passage must keep the reader's drive to know
alive — if it hands an answer to a question they don't have, cut it or reform it into a question.

The existing `~/repos/k8s-learning` repo is **raw material to mine** for Stage 7, not a structure to
copy — its topics are folded into the motivated order above, with anything the fundamentals already
teach removed rather than repeated.
