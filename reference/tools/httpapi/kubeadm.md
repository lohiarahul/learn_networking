# `kubeadm`

What the control plane's own certificates and version skew actually are, and the upgrade plan

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [upgrades and version skew](../../../networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Certificates, version skew, upgrades

| Command | What it gives you |
|---|---|
| `kubeadm certs check-expiration` | every control-plane certificate and its expiry |
| `kubeadm upgrade plan` | which versions are legal from here |
| `kubeadm token list` | join tokens and their TTLs |
| `kubeadm config print init-defaults` | the full config, with defaults filled in |
