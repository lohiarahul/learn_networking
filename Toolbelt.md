# The Toolbelt

Every tool you should be fluent in by the end of this course, in the order the journey introduces them
(see `JOURNEY-MAP.md`). Two kinds, and the difference is the whole pedagogy:

- **Fundamentals** — tools that show you the *raw mechanism*. You reach for these to **understand**:
  read the kernel's own file before the friendly wrapper. Master these and the abstractions stop being
  magic.
- **Modern / production** — the *latest* tools you reach for to **operate** real systems at scale.
  They're only worth using once you know what they're hiding.

You take none of this on our word. Each tool is **earned by comparison** — you meet it against the rival
it beats, or against the raw file it wraps, and feel the difference yourself. (Decode `/proc/net/tcp`
before you trust `ss`; hold `netstat` next to `ss`; feel `strace` stop the world before eBPF rescues
you.) A tool you were merely *told* to use is a tool you don't really understand — so this list is a map
of what to *earn*, in order, not a set of verdicts to memorise.

"Expert" means: when something breaks, you instinctively drop to the fundamental tool to see the truth,
and when you're building, you wield the modern one without ceremony.

> **This file is the roster, not the reference.** It answers *"what should I be fluent in by now?"*, in
> the order the journey introduces things. For *"what does this tool do and how do I spell it"*, the
> [instrument panel](reference/README.md) is the place — sorted for lookup rather than for learning,
> with [the naming grammar](reference/01-the-grammar.md) that makes an unfamiliar command guessable and
> [an index](reference/tools/README.md) that marks every tool **taught** or **roster only**.

> ## ⚑ This is the nine-stage roster, not the built course
>
> The stage headings below run 0–9, because this list is pinned to the *whole* journey. Most of that
> road is now paved:
>
> | Stages | Status |
> |---|---|
> | **0–3** (orientation, Acts I–III), **6** (Act IV), **7** networking and cluster (Acts V–VII, X) | ✅ you meet these tools in a lesson |
> | **4** cryptography (Act VIII) | ✅ six lessons — `openssl dgst`/`-hmac`/`enc`/`genpkey`/`pkeyutl`/`x509`, the full TLS 1.3 handshake rebuilt from parts |
> | **5** identity (Act IX) | ✅ six lessons against a live Keycloak — tokens, sessions, OAuth2/OIDC, RBAC |
> | **8** AWS networking, **9** AWS security | 🔜 **no lessons yet** — treat these sections as a shopping list |
>
> So the honest answer to "where does the course teach this?" is now tool by tool, and the sections
> below mark it: **(taught — …)** means a lesson runs it, and anything unmarked is roster only. The
> ones people arrive looking for: `cosign` and `trivy` are taught in Act X lesson 08, `Falco` in
> lesson 10, `Kyverno` in lesson 05, `External Secrets` in lesson 11, `crictl` and `etcdctl` across
> Acts VI and X, `openssl` throughout Act VIII. `vault` and the `aws` CLI are not taught — those are
> Stages 8–9. See the roadmap banner in [`JOURNEY-MAP.md`](JOURNEY-MAP.md) for exactly where the
> built road ends.

---

## Always-on core (every stage)

`git` · `bash`/`zsh` scripting · `tmux` · a real editor (`vim`/`nvim` or VS Code) · `jq` (JSON) ·
`yq` (YAML) · `ripgrep` (`rg`) · `fzf` · `curl` · `ssh` · `make`/`just`. These never leave your hands.

---

## Stage 0–1 — Process, sockets, the kernel's ledgers

**Fundamentals**
- `/proc` (read it directly — `cat /proc/net/tcp`, `/proc/<pid>/fd/`, `/proc/<pid>/ns/`) — the source of truth.
- `lsof` — every open file/socket, by process.
- `ss` — the modern socket statistics tool (replaces `netstat`); know both.
- `strace` / `ltrace` — watch the actual syscalls (`socket`, `bind`, `read`, `write`).
- `ulimit` / `prlimit` — the file-descriptor ceiling.
- `gcc` / `make` / `gdb` — to build and inspect the course's small C programs.

**Modern / production**
- *Deferred on purpose.* The modern way to watch syscalls live is eBPF (`bpftrace`/`bcc`) — but eBPF is
  a **Stage 7** concept: a `bpftrace` one-liner is a program loaded into the kernel, and you can't
  appreciate that before you understand kernel hooks. Here, `strace` is the right tool; its eBPF
  successor waits until you've earned it.

---

## Stage 2 — Two machines: L2, L3, DNS

**Fundamentals**
- `ip` (the iproute2 suite: `ip addr`, `link`, `route`, `neigh`) — the one tool that replaced `ifconfig`/`route`/`arp`.
- `ping`, `arping` — reachability at L3 and L2.
- `traceroute` / `tracepath` — the path, hop by hop.
- `tcpdump` — capture and read packets from the command line (learn the BPF filter syntax cold).
- `ethtool` — NIC settings, offloads, ring buffers. *(roster only — no lesson runs it, though Act II raises the offload mystery it would explain.)*
- `dig` (+`host`, `nslookup`) — DNS resolution you can read.
- `dhclient` / `networkctl` — how a host gets its address.

**Modern / production**
- `mtr` — continuous traceroute + loss/latency per hop. *(roster only.)*
- `Wireshark` / `tshark` / `termshark` — deep packet analysis with dissectors. *(named on Act II's `in-the-wild` page as tcpdump's visual rival; no lesson runs `tshark` itself.)*
- `nmap` — host/port/service discovery (and the security shadow of scanning).
- `drill` / `dog` / `dnsx` — friendlier, DNSSEC-aware DNS clients.
- `gping` — ping with a live graph.

---

## Stage 3 — TCP, the web, the locked door

**Fundamentals**
- `ss -ti` — live TCP state, RTT, window, retransmits.
- `conntrack` (conntrack-tools) — read the kernel's flow table directly.
- `nc` (netcat) / `socat` — hand-craft TCP/UDP connections; the Swiss-army knives. *(`nc` is taught throughout Act III; `socat` is roster only.)*
- `curl -v` — every byte of an HTTP(S) exchange; the most important tool here.
- `openssl s_client` — open a TLS connection by hand (used as a black box now, opened in Stage 4).

**Modern / production**
- `httpie` / `xh` — ergonomic HTTP clients.
- `iperf3` — throughput testing.
- `wrk` / `k6` / `oha` / `vegeta` — modern HTTP load generation and benchmarking.
- `curl --http3` / `h2load` — exercise HTTP/2 and HTTP/3 (QUIC).

---

## Stage 4 — Cryptography & trust

**Fundamentals**
- `openssl` (the whole suite: `dgst`, `enc`, `genpkey`, `req`, `x509`, `verify`, `s_client`) — the bedrock.
- `sha256sum` / `b2sum` — hashing from the shell.
- `ssh-keygen` — keypairs and signatures you already use daily.
- `gpg` — signing, encryption, the web-of-trust model.

**Modern / production**
- `step` (smallstep CLI) — sane certificate and CA tooling.
- `mkcert` — instant locally-trusted dev certs.
- `cfssl` — CloudFlare's PKI toolkit.
- `age` + `sops` — modern file encryption and secret-in-git encryption.
- `cosign` / Sigstore — sign and verify artifacts and container images (supply-chain trust).
- `cert-manager` — automated certificate issuance/renewal (lands properly in Stage 7).

---

## Stage 5 — Identity & access

**Fundamentals**
- `jq` + a JWT decoder (`jwt-cli`) — inspect and verify tokens by hand.
- `ldapsearch` — query the directory where identity actually lives.
- `openssl`/`curl` — drive OAuth2/OIDC token endpoints manually to see the flow.

**Modern / production**
- `Keycloak` (or `Dex`, `Authentik`, `Ory`) — identity providers (OIDC/SAML).
- `oauth2-proxy` — bolt authentication in front of any service.
- `step oauth` — fetch OIDC tokens from the CLI.

---

## Stage 6 — Containers (one machine pretends to be many)

**Fundamentals**
- `ip netns`, `nsenter`, `unshare` — build and enter namespaces by hand (containers, demystified). *(`ip netns` is taught in Act IV and `unshare` in Act X; `nsenter` is named in prose and never run — [derive it yourself](reference/06-derive-it.md#ladder-1--derive-the-command).)*
- `iptables` / `nft` — the NAT and filtering rules a container runtime writes for you. *(`iptables` is taught in Act IV; `nft` is roster only — zero lesson uses, despite being the modern replacement.)*
- `bridge` — manage the virtual switch (`docker0` and friends).
- `runc` / `crun` — the OCI runtime that actually starts a container.

**Modern / production**
- `docker` + `docker compose` — the ubiquitous developer interface.
- `podman` + `buildah` — daemonless, rootless containers and builds.
- `nerdctl` + `containerd`/`ctr` + `crictl` — the runtime stack Kubernetes really uses.
- `BuildKit` / `ko` — fast, reproducible image builds.
- `skopeo` (move/inspect images) · `dive` (inspect image layers) · `trivy` (scan images).

---

## Stage 7 — Kubernetes

**Fundamentals (see the mechanism)**
- `kubectl` — the universal client; learn `explain`, `get -o yaml`, `describe`, `debug`, `auth can-i`.
- `etcdctl` — read the cluster's actual stored state; back it up and restore it. (taught — Act VI [`05-etcd-backup-and-restore.md`](networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md))
- `crictl` — talk to the node's container runtime directly when `kubectl` can't. (taught — Act VI [`02-static-pods.md`](networking-fundamentals/act-6-control-plane/02-static-pods.md) and [`08-when-the-control-plane-breaks.md`](networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md))
- `kubeadm` / `kind` / `k3s`+`k3d` / `minikube` — stand up clusters (kind for this course).
- node-level `iptables` / `cilium` BPF maps — see how a Service is actually implemented.

**Modern / production — daily driving**
- `k9s` — the terminal UI you'll live in · `stern` (multi-pod logs) · `kubectx`/`kubens`.
- `krew` plugins: `tree`, `neat`, `who-can`, `access-matrix`, `df-pv`, `node-shell`, `sick-pods`.

**Networking & mesh**
- `Cilium` (taught — Act X [`09-encryption-between-pods.md`](networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md), with WireGuard in the datapath; `Hubble` is named but **not** run anywhere in the course) ·
  `Calico` (taught — Act V [`01-lab-with-kind.md`](networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md), as the CNI that actually enforces NetworkPolicy) · `MetalLB` · `ingress-nginx` · **Gateway API** (taught — Act V
  [`06b-gateway-api.md`](networking-fundamentals/act-5-kubernetes/06b-gateway-api.md), with
  `nginx-gateway-fabric` as the controller) · `Istio`/`Linkerd` (service mesh).

**Packaging, delivery, platform**
- `Helm` and `Kustomize` (both taught — Act VII [`08-shipping-a-set-of-objects.md`](networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md)) · `helmfile` · `cdk8s` · `ArgoCD`/`Flux` (GitOps) · `Crossplane` (cloud from a claim).

**Security (CKS)**
- `OPA Gatekeeper` and `Kyverno` (policy — both taught, Act X [`05-policy-as-a-product.md`](networking-fundamentals/act-10-cluster-security/05-policy-as-a-product.md)) ·
  `kube-bench` (CIS — taught, Act X [`07-the-doors-left-open.md`](networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md)) ·
  `Trivy` and `cosign` (posture and provenance — both taught, Act X [`08-what-you-shipped.md`](networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md)) ·
  `Falco` (runtime — taught, Act X [`10-seeing-it-happen.md`](networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md)) ·
  `External Secrets` (taught, Act X [`11-secrets-from-outside.md`](networking-fundamentals/act-10-cluster-security/11-secrets-from-outside.md), against its `fake` provider so no account is needed) ·
  `kubescape` / `Polaris` · `kubeseal`/Sealed Secrets · a real secret store behind External Secrets.
- **Named as gaps, honestly:** `bom` (the SBOM tool the exam whitelists — the course teaches Trivy's SBOM instead), `kubesec`, `kube-linter`, `aa-status`, and sigstore keyless signing. [`exam-prep/`](exam-prep/README.md) says so in the domain maps; no lesson closes them.

**Scaling & observability**
- `metrics-server` · `KEDA` · Cluster Autoscaler · `Velero` (DR) · `Kubecost` ·
  `kube-prometheus-stack` (Prometheus + Grafana + Alertmanager) · `Loki` · `Jaeger`/`OpenTelemetry` ·
  `bpftrace`/`bcc`/`Pixie` (eBPF tracing — the near-zero-overhead successor to `strace`, finally appreciable now that you understand kernel hooks).

**Validation**
- `kubeconform` / `datree` / `kubent` — catch broken or deprecated manifests before they ship.

---

## Stage 8 — AWS networking

**Fundamentals**
- `aws` CLI (+ CloudShell) — the direct API; everything else wraps this.
- `LocalStack` — run AWS APIs offline so you can lab without an account or a bill.
- VPC **Reachability Analyzer** / **Network Access Analyzer** — prove (or disprove) a path.
- VPC **Flow Logs** queried with **Athena** — the cloud's conntrack record.

**Modern / production (Infrastructure as Code)**
- `Terraform` / **`OpenTofu`** — the standard for declaring cloud infra.
- `Pulumi` · AWS CDK · CloudFormation — alternatives you should recognise.
- `Crossplane` — provision AWS from inside Kubernetes (the Stage 7 bridge).
- `Steampipe` — query your live cloud with SQL (superb for auditing networks).

---

## Stage 9 — AWS security

**Fundamentals**
- IAM **Access Analyzer** + **Policy Simulator** — reason about least privilege precisely.
- `CloudTrail` (every API call) · `AWS Config` (compliance state) — the evidence trail.
- `KMS` / `CloudHSM` / `ACM` / `Secrets Manager` — encryption and key/secret management.

**Modern / production**
- **`Prowler`** · **ScoutSuite** — automated security assessments across an account.
- **`Steampipe`** — SQL queries for IAM/exposure audits.
- **Cloud Custodian** — policy-as-code guardrails and auto-remediation.
- `Checkov` / `tfsec` / `cfn-nag` — scan IaC for misconfigurations before deploy.
- `pmapper` / `Cartography` — graph IAM and resource relationships to find attack paths.
- AWS-native: **GuardDuty**, **Security Hub**, **Detective**, **Macie**, **Inspector** — detection at scale.
- `Pacu` — offensive AWS framework (for authorised testing — understand attacks to defend).

---

## How to read your own progress

By the end of each stage you should be able to pick the right tool *without thinking* — the fundamental
one to see what's really happening, the modern one to get the job done. This file grows with the
journey: whenever a stage's content changes in `JOURNEY-MAP.md`, the tools here change with it.
