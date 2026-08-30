# `runc` — run container

The OCI runtime that actually creates the namespaces and cgroups. Below every higher-level tool

| | |
|---|---|
| **Speaks** | [`nsapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [who does this for you](../../../networking-fundamentals/act-4-one-pretends-many/05-who-does-this-for-you.md) (built and run directly); named again in [the kernel says no](../../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md), where a Kubernetes Pod dies inside it |
| **In the lab** | ❌ not installed in `netlab:latest` — but `apk add runc` puts it in the Act IV `netshoot` lab, which already runs `--privileged` |
| **Blind spot** | `nsapi` cannot tell you what is *inside* a namespace. These move you between namespaces; they read nothing — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### The runtime that actually makes the namespaces

| Command | What it gives you |
|---|---|
| `runc list` | containers this runtime knows about |
| `runc state <id>` | its config and PID |
| `runc spec` | generate a default config.json — the OCI contract, readable |
