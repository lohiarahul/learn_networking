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

> ## ⚑ This is the nine-stage roster, not the built course
>
> The stage headings below run 0–9, because this list is pinned to the *whole* journey. Only some of
> that road is paved:
>
> | Stages | Status |
> |---|---|
> | **0–3** (orientation, Acts I–III), **6** (Act IV), **7** networking (Act V) | ✅ you meet these tools in a lesson |
> | **4** cryptography, **5** identity, **8** AWS networking, **9** AWS security | 🔜 **no lessons yet** — treat these sections as a shopping list |
>
> So if you came here looking for where the course teaches `vault`, `aws`, or `cosign`: it doesn't, yet.
> Those sections describe the destination. See the roadmap banner in [`JOURNEY-MAP.md`](JOURNEY-MAP.md)
> for exactly where the built road ends.

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
- `ethtool` — NIC settings, offloads, ring buffers.
- `dig` (+`host`, `nslookup`) — DNS resolution you can read.
- `dhclient` / `networkctl` — how a host gets its address.

**Modern / production**
- `mtr` — continuous traceroute + loss/latency per hop.
- `Wireshark` / `tshark` / `termshark` — deep packet analysis with dissectors.
- `nmap` — host/port/service discovery (and the security shadow of scanning).
- `drill` / `dog` / `dnsx` — friendlier, DNSSEC-aware DNS clients.
- `gping` — ping with a live graph.

---

## Stage 3 — TCP, the web, the locked door

**Fundamentals**
- `ss -ti` — live TCP state, RTT, window, retransmits.
- `conntrack` (conntrack-tools) — read the kernel's flow table directly.
- `nc` (netcat) / `socat` — hand-craft TCP/UDP connections; the Swiss-army knives.
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
- `ip netns`, `nsenter`, `unshare` — build and enter namespaces by hand (containers, demystified).
- `iptables` / `nft` — the NAT and filtering rules a container runtime writes for you.
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
- `etcdctl` — read the cluster's actual stored state; back it up and restore it.
- `crictl` — talk to the node's container runtime directly when `kubectl` can't.
- `kubeadm` / `kind` / `k3s`+`k3d` / `minikube` — stand up clusters (kind for this course).
- node-level `iptables` / `cilium` BPF maps — see how a Service is actually implemented.

**Modern / production — daily driving**
- `k9s` — the terminal UI you'll live in · `stern` (multi-pod logs) · `kubectx`/`kubens`.
- `krew` plugins: `tree`, `neat`, `who-can`, `access-matrix`, `df-pv`, `node-shell`, `sick-pods`.

**Networking & mesh**
- `Cilium` + `Hubble` (eBPF CNI, observability — the future of cluster networking) ·
  `Calico` · `MetalLB` · `ingress-nginx` · Gateway API · `Istio`/`Linkerd` (service mesh).

**Packaging, delivery, platform**
- `Helm` + `helmfile` · `Kustomize` · `cdk8s` · `ArgoCD`/`Flux` (GitOps) · `Crossplane` (cloud from a claim).

**Security (CKS)**
- `OPA Gatekeeper` / `Kyverno` (policy) · `kube-bench` (CIS) · `Trivy` / `kubescape` / `Polaris` (posture) ·
  `Falco` (runtime) · `cosign` (provenance) · `kubeseal`/Sealed Secrets · `External Secrets` + `Vault`.

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
