# `wg` — WireGuard

The live tunnel state — peers, handshakes, keys — under Cilium's or anyone else's encryption

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [encryption between Pods](../../../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Live tunnel state

| Command | What it gives you |
|---|---|
| `wg show` | peers, public keys, allowed IPs, last handshake, bytes |
| `wg show <dev> latest-handshakes` | the field that says whether a peer is actually alive |
| `wg genkey \| tee priv \| wg pubkey` | a keypair |
| `wg setconf <dev> <file>` | apply a configuration |
