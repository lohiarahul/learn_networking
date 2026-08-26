# `trivy`

Known vulnerabilities and an SBOM for an image you are about to ship

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | read-only |
| **Taught in** | [what you shipped](../../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `trivy --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--severity` | which findings count. Everything is noise until you pick a floor |
| `--exit-code` | fail the process on a finding, which is what turns a report into a gate |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### What you are about to ship

| Command | What it gives you |
|---|---|
| `trivy image <img>` | known vulnerabilities by severity |
| `trivy image --severity HIGH,CRITICAL --exit-code 1 <img>` | the CI-gate form |
| `trivy image --format cyclonedx -o sbom.json <img>` | an SBOM |
| `trivy fs .` | scan a directory, including IaC misconfiguration |
