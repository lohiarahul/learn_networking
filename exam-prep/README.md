# Exam prep — CKA and CKS

**This directory is deliberately not teaching.**

Everything in `networking-fundamentals/` follows one rule: never hand you an answer to a question
you don't yet have. This directory breaks that rule on purpose. A certification exam is 2 hours
against 15–20 hands-on tasks, and what decides the outcome is speed and recall — which is
*banking*, exactly what the course refuses to do. Both goals are legitimate; they just can't share
a page without spoiling each other.

So: work the acts to understand Kubernetes. Come here in the last few weeks to rehearse for a
clock. The domain maps below exist to tell you honestly which parts of the exam the course has
covered and which it hasn't.

`tools/check_pedagogy.py` skips this directory for the Predict-first and ladder invariants (see
`is_lesson()` there). Link integrity still applies — a dead link into a lesson is a real defect.

## The two exams

|  | CKA | CKS |
|---|---|---|
| Curriculum version | **v1.35** | **v1.34** *(document lags; the environment runs v1.35)* |
| Duration | 2 hours | 2 hours |
| Tasks | 15–20 performance-based (candidates report 16–17) | 15–20 |
| **Pass mark** | **66%** | **67%** |
| Kubernetes version | v1.35 | v1.35 |
| Price | $445 | $445 |
| Attempts included | 2 (one free retake) | 2 (one free retake) |
| Eligibility window | 12 months to schedule | 12 months |
| Validity | **2 years** | **2 years** |
| Prerequisite | none | **must have passed CKA — active status *not* required** |
| Results | emailed within 24 hours | same |

Two things worth knowing before you spend the money:

- **CKS does not need a *current* CKA.** Any achieved CKA qualifies you to schedule CKS, even an
  expired one. This is a change from the older rule.
- **From 18 June 2026, the CARE program means passing or recertifying CKS reinstates or extends
  your CKA**, with the expiry dates synchronised. So the two certifications are less independent
  than the $445 + $445 framing suggests.

Tasks are **any order and equally weighted**, and you do not need to finish. One reported candidate
answered 13 of 16 and scored 84%. The margin cuts both ways — another lost three questions to a
client crash and scored 62%, four points short.

## The domain maps

- **[CKA domain map](cka-domain-map.md)** — every domain and sub-competency, with a link to the
  lesson that covers it and an honest gap marker where nothing does.
- **[CKS domain map](cks-domain-map.md)** — the same for CKS.

Both are transcribed from the official PDFs in
[`github.com/cncf/curriculum`](https://github.com/cncf/curriculum), cross-checked against the Linux
Foundation program-changes pages. **Re-pull them before you book.** The curricula are versioned per
Kubernetes release and the weightings on most third-party sites are wrong — one popular blog
publishes an invented 12/22/31 split for CKA.

## The rest of this directory

- **[kubectl-speed.md](kubectl-speed.md)** — what actually saves time in the current environment.
  Read the warning at the top: the familiar `alias k=kubectl` ritual is now mostly wasted keystrokes.
- **[exam-day.md](exam-day.md)** — the environment, its friction, and the time-management sweep.

## Practice resources that are actually current

**killer.sh** ([cka](https://killer.sh/cka) · [cks](https://killer.sh/cks)) — **two sessions ship
with your exam registration**; activate them from the LF portal. Each gives 36 hours wall-clock
containing a 120-minute timed run you may restart freely, with 17 scenarios and full solutions. The
two sessions have *different* question sets. It is the only environment that reproduces the
SSH-per-task structure of the real exam, which by itself justifies using both — one about two weeks
out to find gaps, one within 72 hours of the exam under real conditions.

Its one flaw: the CKS set still includes Dashboard hardening, Dockerfile hardening and OPA
Gatekeeper, all of which map to competencies **removed in October 2024**. Use it; don't treat it as
the curriculum.

**Killercoda** — free, and all the scenarios that matter are Kim Wüstkamp's (the killer.sh author):

- [killercoda.com/cka](https://killercoda.com/cka) — the current consolidated CKA course
- [killercoda.com/killer-shell-cka](https://killercoda.com/killer-shell-cka) — legacy, but has the
  strong troubleshooting scenarios (`apiserver-crash`, `apiserver-misconfigured`)
- [killercoda.com/killer-shell-cks](https://killercoda.com/killer-shell-cks)
- [remote-desktop rehearsal](https://killercoda.com/kimwuestkamp/scenario/cks-cka-ckad-remote-desktop)
  — practise the actual XFCE exam UI. Underrated; the UI costs people real minutes.

**Free written guides that are genuinely post-2025:**
[`techiescamp/cka-certification-guide`](https://github.com/techiescamp/cka-certification-guide)
(targets v1.35 explicitly) and
[`bmuschko/cka-study-guide`](https://github.com/bmuschko/cka-study-guide) (dedicated chapters for
Operators/CRDs, Helm+Kustomize, and Gateway API). For CKS use
[`bmuschko/cks-crash-course`](https://github.com/bmuschko/cks-crash-course) — **not** his
`cks-study-guide`, which was last updated August 2024 and pre-dates the CKS revision.

**Stale — do not use as a coverage checklist:** both `walidshaari` repos (organised around "CKA 2023
objectives" and CKS v1.26 respectively, with pre-revision weightings), and
`stackrox/Kubernetes_Security_Specialist_Study_Guide` (CKS v1.19, leads with PodSecurityPolicy,
which was removed from Kubernetes in 1.25). Also: `dgkanatsios/CKAD-exercises` is excellent but is
**CKAD** — it has no Kustomize and no Gateway API, so it is not a CKA syllabus.

## Allowed documentation — read this as a coverage signal

The Linux Foundation only whitelists docs for tools the exam expects you to consult, which makes
this list evidence about what is examined.

**CKA:** `kubernetes.io/docs` (all translations) · `kubernetes.io/blog` · **`helm.sh/docs`** ·
**`gateway-api.sigs.k8s.io`** · task-specific links in the Quick Reference box.

**CKS** adds: `falco.org/docs` · **`kubernetes-sigs.github.io/bom/cli-reference/`** ·
`etcd.io/docs` · `kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/` ·
`docs.cilium.io/en/stable` · `istio.io/latest/docs`.

Plus, for both: documentation installed by the distribution — so **man pages are in scope** — and
you may install distro packages.

Two inferences worth banking. First, `helm.sh` and `gateway-api.sigs.k8s.io` being on the CKA list
is independent confirmation that Helm and Gateway API are genuinely examined. Second, and
under-appreciated: **`kustomize.io` is NOT allowed.** Your only Kustomize reference is one page
inside kubernetes.io, which makes Kustomize disproportionately hard and means you must know it from
memory.

**Not allowed, contrary to several popular 2025 guides:** Trivy, AppArmor, kube-bench, Kyverno,
OPA/Gatekeeper, sigstore/cosign, gVisor, Kubesec, KubeLinter. Plan on not having them. For those
tools the escape hatch is the task's own Quick Reference box, plus `--help` and man pages.
