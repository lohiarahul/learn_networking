# Exam day

The environment costs people marks. Not the Kubernetes — the environment. This page is the part that
has nothing to do with knowing Kubernetes and everything to do with passing.

## The structure, which changed in 2025

The exam runs on **PSI's Bridge platform**: a remote **XFCE Linux desktop** over VNC, inside the PSI
Secure Browser. It is not Killercoda — Killercoda is the practice platform by the same author as
killer.sh.

The important part:

> You start on a **base node** (hostname `base`). **Each task names a host you `ssh` into.**
> **Nested SSH is not supported** — you `exit` back to `base` between tasks.
> **Do not reboot `base`.**

Three consequences that invalidate older advice:

1. **`kubectl config use-context` is no longer how you switch between clusters.** Any guide that
   says so is pre-February-2025. You switch by SSH-ing to a different host.
2. **Your shell setup does not persist.** Aliases and exports die when the session ends. See the
   warning at the top of [kubectl-speed.md](kubectl-speed.md) — `kubectl`, the `k` alias and bash
   completion are already installed on the SSH hosts, so there is nothing to set up anyway.
3. **The most-cited time sink is SSH churn itself.** Named as gotcha #1 in a May 2025 report:
   *"manually exiting previous clusters and SSHing into new ones consumes significant time."* Worse
   is the failure mode from a March 2026 report — starting a task without SSH-ing to the named host
   first, then debugging a problem that doesn't exist because you're in the wrong cluster.

**Read the host name in every task before you touch anything.**

## The first 60 seconds

Do these before task 1. They pay for themselves several times over.

- **Terminal → Preferences: enable "Copy on Select" and "Paste on Right Click."** There is a 1–2
  second clipboard lag copying out of the question panel, and you will do it dozens of times.
- **Open the Kubernetes docs tab yourself.** It does **not** auto-open. One report puts it bluntly:
  *"memorizing `https://kubernetes.io/docs` is essential."*
- **`:set expandtab tabstop=2 shiftwidth=2`** in vi, on the first host you land on.

## Keys and clipboard

| Action | Key |
|---|---|
| Copy/paste **in the terminal** | `Ctrl+Shift+C` / `Ctrl+Shift+V` |
| Copy/paste **everywhere else** | `Ctrl+C` / `Ctrl+V` |
| Close a window — **NOT `Ctrl+W`** | `Ctrl+Alt+W` |
| Root shell | `sudo -i` |

**`Ctrl+W` closes your browser tab.** Muscle memory from a text editor will cost you the docs tab.
The **INSERT key is disabled** — press `i` in vi.

Two more: **`Ctrl+F` is unreliable** on the remote desktop (sources disagree on whether it works at
all), so don't plan to search a docs page — plan to know where the page is. And there is a GUI
editor (VSCodium under Applications → Development, as of a March 2025 report), but earlier
environments shipped Mousepad with a nasty trap: **Mousepad and the File Manager saw a different
filesystem than the terminal.** Verify on the day before trusting a GUI editor with a file path.

## The sweep

**17 tasks, 120 minutes, ≈7 minutes each. Any order. Equally weighted.**

Two passes:

1. **Pass one — harvest.** Go start to finish. 3–5 minutes on anything easy. **The moment a task
   passes 10 minutes, flag it and move on.** Do not fight.
2. **Pass two — the flagged ones**, hardest last. Aim to have 10–15 minutes left for a review sweep.

> **Where to practise this, because reading it does nothing.** All ten of the course's `diagnose.md`
> drill sets now carry a per-drill **target time** and the 10-minute walk-away rule, keyed to this
> paragraph: [Act I](../networking-fundamentals/act-1-one-machine/diagnose.md) ·
> [II](../networking-fundamentals/act-2-two-machines/diagnose.md) ·
> [III](../networking-fundamentals/act-3-the-internet/diagnose.md) ·
> [IV](../networking-fundamentals/act-4-one-pretends-many/diagnose.md) ·
> [V](../networking-fundamentals/act-5-kubernetes/diagnose.md) ·
> [VI](../networking-fundamentals/act-6-control-plane/diagnose.md) ·
> [VII](../networking-fundamentals/act-7-workloads/diagnose.md) ·
> [VIII](../networking-fundamentals/act-8-trust/diagnose.md) ·
> [IX](../networking-fundamentals/act-9-identity/diagnose.md) ·
> [X](../networking-fundamentals/act-10-cluster-security/diagnose.md). That is **53 timed
> symptom-first exercises**, which is the only artifact in this repo shaped like an exam task. Acts V,
> VII, IX and X are the ones whose subject matter the exams actually cover; Acts I–IV build the
> reflex on cheaper ground.



**Do the broken-cluster troubleshooting tasks last.** Two independent sources say this, and the logic
is sound: Troubleshooting is 30% of the marks but close to 90% of the time-sink risk. A task that
eats 25 minutes has cost you three others worth the same marks.

**You do not need to finish.** One reported candidate answered 13 of 16 and scored 84% against a 66%
pass mark. But the margin cuts both ways: another lost three questions to a client crash and scored
62% — four points short.

**The dependency trap:** a mistake on one cluster can break a later task on the same cluster. Skim
every task that touches a cluster before you start mutating it.

## Partial credit and reading the task

Read the whole task before typing. Specifically:

- **Do exactly what is asked and no more.** Extra remediation earns nothing and can break a graded
  condition. This is called out explicitly for Trivy tasks in CKS.
- **Note the host.** Some tools live only on the control plane.
- **Note the namespace**, then set it once:
  `kubectl config set-context --current --namespace=<ns>`.
- **Note where output is supposed to go.** Tasks often ask for a file at a specific path. Pipe
  directly to it rather than retyping.
- **Back up before editing anything in `/etc/kubernetes/manifests/`.** A typo in
  `kube-apiserver.yaml` takes down the API server, and then you have no `kubectl` with which to fix
  it. `cp kube-apiserver.yaml /tmp/` first, every time.

## Reliability — this genuinely fails people

Two documented losses: one attempt ended when the PSI Secure Browser closed itself due to **thermal
throttling**; another when video froze after 12 of 17 questions. Mitigations candidates recommend:

- **15–20 GB free disk**, and keep the machine physically cool
- Wired network if possible, with a phone hotspot as failover; a UPS if your power is unreliable
- **A genuinely quiet, private room** — *"even slight noise will be pointed out"* by the proctor
- **Single monitor**, 15"+ and 1080p recommended
- Expect **~50–100 ms keyboard latency**, sluggish Firefox scrolling, and laggy window drags. It has
  been VNC-based since the 2022 PSI Bridge migration and there is a long complaint history on the LF
  forum.
- Expect **lower screen resolution than killer.sh gave you**. Practise on the
  [remote-desktop rehearsal scenario](https://killercoda.com/kimwuestkamp/scenario/cks-cka-ckad-remote-desktop)
  so the UI is not a surprise.

## Booking and retakes

- **Two attempts are included** with each registration — one free retake. You have a **12-month
  eligibility window** to schedule.
- **killer.sh: two sessions ship with your registration**, activated from the LF portal. Each is 36
  hours wall-clock containing a 120-minute timed run you can restart freely, with 17 scenarios and
  full solutions. **The two sessions have different question sets.** Use one about two weeks out to
  find gaps, and one within 72 hours of the exam under real conditions — it is the only environment
  that reproduces the SSH-per-task structure.
- Results arrive by email **within 24 hours**.
- **Certifications are valid 2 years.**
- **CKS does not require an *active* CKA** — any achieved CKA qualifies, even an expired one. And
  under CARE (in force since **18 June 2026**), passing or recertifying CKS **reinstates or extends
  your CKA**, with expiry dates synchronised.

## Calibration against killer.sh

Killer Shell's own framing has long been that it is *"more difficult than the real certification."*
That has shifted post-2025: a January 2026 report calls the real CKA *"comparable to Killer Shell
simulator level"*, and a May 2026 one describes killer.sh as *"denser than the real exam"* rather
than harder per question. For CKS, 2026 guides call the two comparable.

So treat a killer.sh score as roughly predictive rather than pessimistic — and don't assume the real
exam will feel easier.

One caveat worth repeating: **killer.sh's CKS set still includes Dashboard hardening, Dockerfile
hardening and OPA Gatekeeper**, all of which map to competencies **removed in October 2024**. It is
the best simulator available and it is not the curriculum. The
[CKS domain map](cks-domain-map.md) is.

---

↑ Back to **[exam prep](README.md)** · **[CKA domain map](cka-domain-map.md)** ·
**[CKS domain map](cks-domain-map.md)**
