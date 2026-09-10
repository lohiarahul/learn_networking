# Docker networks

**The wall** — Three containers are running on your machine right now. You've just spent an entire lesson building veth pairs and bridges by hand, so you go looking for them the way you'd look for anything else in this course: as a file. `ls /sys/class/net/docker0/brif/`. It comes back empty — or on Docker Desktop, there's no `/sys/class/net` to even ask, because your shell isn't in the namespace that has one.

`/sys/class/net` always reflects *whoever's asking*. `docker` itself is just a client talking to the daemon over a socket — no kernel namespace required — so every `docker ...` command below still runs in your normal terminal, same as always. But `docker0` is kernel state sitting in the *root* network namespace (the VM's, on Docker Desktop), and your terminal was never in that namespace. To peek at it, open a **second terminal window or tab** — leave your first one alone — and start a shell that *is* in that namespace, the same trick [lesson 02](02-veth-and-bridge.md) used:

```bash
docker run --rm -it --privileged --network host nicolaka/netshoot
```

Call that second window the **peek shell**. Lesson 02 ran everything inside one privileged shell start to finish; here you run two terminals side by side instead. Below, every `ls /sys/class/net/...` and `ip link` command runs in the peek shell (the second window); every `docker ...` command runs in your normal terminal (the first).

Don't want two windows open? Skip the interactive peek shell entirely and run each check as its own throwaway container instead — same namespace visibility, no second window to manage:

```bash
docker run --rm --privileged --network host nicolaka/netshoot ls /sys/class/net/docker0/brif/
```

Wherever you see a peek-shell command below, this is the one-liner form of it — just swap in the path or `ip link` arguments. Three containers running, bridge showing no ports — nothing's broken. `docker run` builds one of several different object sets depending on a flag you may not have been passing, and only one of those sets involves `docker0` at all.

### The four shapes a container's networking can take

`--network` doesn't configure a network the way an IP address configures a route. It picks *which of the last lesson's objects get built at all* — for some modes, none of them do:

| Mode | How you ask for it | What actually gets created | Where you'd find it |
|---|---|---|---|
| **bridge** (the default) | nothing, or `--network bridge` | a veth pair, one end plugged into `docker0` as a port | `/sys/class/net/docker0/brif/` |
| **host** | `--network host` | *(predict this one below, then check)* | *(predict this one below, then check)* |
| **none** | `--network none` | a bare namespace with only `lo` — exactly [lesson 01](01-namespaces.md)'s fresh, empty namespace, deliberately never wired to anything | `ip netns`-style isolation, no veth at all |
| **custom / user-defined** | `docker network create mynet` first, then `--network mynet` | *(predict this one below, then check)* | *(predict this one below, then check)* |

That table is a claim, not a fact, until you've checked it against your own containers. Don't guess which row you're in — `-f`/`--format` takes a small Go template; `{{.HostConfig.NetworkMode}}` means "the `NetworkMode` field, nested under `HostConfig`, from the JSON `docker inspect` would otherwise print in full":

```bash
docker inspect -f '{{.HostConfig.NetworkMode}}' <container-name>   # your terminal — "host", "bridge", or a custom network's name
```

> **Predict first —** `host` mode hands the container the existing host namespace outright, rather than building it a fresh one the way `bridge` mode does. Given that, and given what you know from [lesson 02](02-veth-and-bridge.md) about how a veth pair gets plugged into a bridge, what do you expect `/sys/class/net/docker0/brif/` to contain the moment you start a `--network host` container — one new entry, or none?

```bash
docker run -d --network host --name hosttest nicolaka/netshoot sleep 60   # your terminal
ls /sys/class/net/docker0/brif/        # peek shell — unchanged from before this line
docker rm -f hosttest                                                     # your terminal
```

Nothing changed, because `--network host` never asked the kernel to build a veth pair in the first place — there's no cable, so there's nothing to plug into `docker0`. Compare that against the mode that *does* build one:

```bash
docker run -d --name bridgetest nginx      # your terminal — no --network flag at all = bridge, the default
ls /sys/class/net/docker0/brif/            # peek shell — one new veth, e.g. veth66bff93
docker rm -f bridgetest                    # your terminal
```

Same command, one flag different, and only one leaves a trace under `/sys`. `docker0/brif/` was never lying to you — it was accurately reporting that a `--network host` container has no veth, because Docker never built one.

### The naming quirk that hides custom networks even harder

`docker network create` builds you a real Linux bridge — but not one named after your network. Make one and ask Docker for its ID:

```bash
docker network create testnet                                    # your terminal
docker network inspect testnet --format '{{.Id}}'                 # your terminal
# e.g. 6fcd65fa1dbc2e19c3a8...
```

and the kernel bridge sitting behind that name is `br-6fcd65fa1dbc` — the network's ID, truncated to its first 12 hex characters, with `br-` glued on the front. `br-` is 3 characters, 12 hex characters is 15.

> **Predict first —** Linux interface names have a hard length limit. `br-` plus 12 hex characters lands at exactly 15 — comfortably under that limit, or suspiciously exact? Add one more character and find out. Creating a link needs elevated kernel privilege, so this runs in the peek shell:

```bash
ip link add br-6fcd65fa1dbc type bridge     # peek shell — 15 chars — created
ip link del br-6fcd65fa1dbc                 # peek shell
ip link add br-6fcd65fa1dbc9 type bridge    # peek shell — 16 chars — rejected outright
```

That fails with `Attribute failed policy validation` — a kernel error, not a Docker one. 15 usable characters (`IFNAMSIZ - 1`) is the actual ceiling, not a style choice. A 64-character network ID can't become an interface name at all; truncating to 12 hex characters (the same trick `docker ps` uses for short container IDs) is the only way to fit an identifier under that ceiling and still have it mean something.

> **Predict first —** attach a container to `testnet`. Before you run anything, predict: will it show up under `docker0/brif/` at all?

```bash
docker run -d --network testnet --name nettest nicolaka/netshoot sleep 60   # your terminal
docker network inspect testnet --format '{{.Id}}'   # your terminal — copy the first 12 hex characters
ls /sys/class/net/br-<those 12 characters>/brif/     # peek shell — the actual bridge you found above
```

It never shows up on `docker0` — `docker network create` built its own bridge the moment you ran it, and `nettest`'s veth is a port on `br-<id>` instead. `docker0/brif/` staying empty here looks identical to a `--network host` container leaving it empty, but the reasons are unrelated. Same symptom, two different causes — that's the trap this lesson closes.

If you've already worked with `kind` (Act V introduces it properly; skip this paragraph if you haven't touched it yet), the exact same trick applies to a running cluster: `docker network inspect kind --format '{{.Id}}'` maps to `br-<its first 12 hex characters>`, and every node's veth lives there — never on `docker0` either.

Verify who's actually plugged into which bridge without touching `/sys` at all, the same question asked in Docker's own vocabulary:

```bash
docker network inspect bridge --format '{{json .Containers}}'    # your terminal — who's really on docker0, right now — likely {}
docker network inspect testnet --format '{{json .Containers}}'   # your terminal — who's really on testnet's own bridge — should show nettest
```

(`json` here just renders the field as JSON text instead of Go's default struct dump.)

**Tear it down** — remove the container and the network so `testnet` is free to build again:

```bash
docker rm -f nettest          # your terminal
docker network rm testnet     # your terminal
```

> **You understand this when you can** look at any running container and say, before checking, whether it has a veth at all — and if it does, name the exact bridge interface it's plugged into, `docker0` or `br-<id>`, without Docker ever showing you that interface's name directly.

**Kubernetes sees this as** — a preview of a problem Act V solves properly. `docker0` is one bridge, one node, one hand-typed convention. A cluster CNI plugin builds the *same* kind of bridge (`cni0`, or something plugin-specific) automatically per node, and it faces the exact naming problem you just watched Docker solve for one network: Pod network identifiers are long, generated, and have to become short kernel objects somehow. You now know the shape of that problem before you ever see a CNI config file.

---

← Prev: **[veth and bridge](02-veth-and-bridge.md)** · ↑ **[Act IV overview](README.md)** · Next: **[iptables and NAT](03-iptables-and-nat.md)** →
