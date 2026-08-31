# Act IV — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act IV. This checks whether you can *use* it. Real
failures never arrive labelled "this is a missing MASQUERADE" or "that veth is down" — they arrive as a
symptom, a shrug, and a ticket. Each drill below puts your machine into a **real broken state** (not a
story), hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or
   tool would prove it — *then* look.
3. **Open the reveal only after you've tried.**
4. **Then verify it — and say what was wrong.** Every drill ends with a `Verify it` line:

   ```bash
   tools/verify-drill.sh act-4 <n> "your one-line diagnosis"
   ```

   Run it **from your repository checkout on the host, not from inside the lab container** — and run it
   **before** the drill's `Cleanup` line, because everything it checks lives in the namespaces and rules
   that line destroys. It reaches into the container through `docker exec`, which is why the container
   has to be named `lab` (set `LAB=<name>` if yours is not). It exits `0` only if the machine genuinely
   works again **and** the cause you typed is right, and the checks are function-level on purpose: a
   1450-byte ping with `DF` set rather than a default 56-byte one, a bridge that has *learned* two MACs
   rather than a link that merely reads `UP`, an fd count taken before and after twenty connections. It
   will not tell you the answer — see [`drills/`](../../drills/README.md) for why the expected cause is
   stored as a hash.

**Where:** inside the lab container with the host's real network attached —
`docker run --rm -it --privileged --network host nicolaka/netshoot`. Each drill builds its **own**
namespaces and veths from scratch (the same commands you ran in lessons 1–3), so run a drill's
`Cleanup` line before starting the next one — and everything is wiped entirely on `exit`. The
`--privileged` flag is what lets you create namespaces, move interfaces, and write NAT rules.

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Five rather than seven minutes on most of them, because each of these drills has a narrower surface than an exam task — one machine, or two, and a handful of files.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 5 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

## Drill 1 — "The new container can reach the host but not the internet"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We wired up a fresh container-style namespace. It can ping its own gateway, DNS is
> configured, forwarding is on — but every ping to the outside times out. The host itself reaches
> `8.8.8.8` fine. Same kernel, same uplink. Why can the host get out and the namespace can't?"*

> **⚠ On Docker Desktop this drill's symptom may not appear, for a reason worth more than the drill.**
> The namespace will reach `8.8.8.8` *before* you add any `MASQUERADE` rule. Nothing is wrong with your
> setup: a Docker Desktop container's uplink faces a **userspace network stack** in the VM rather than a
> real L3 forwarder, so the private source address is rewritten outside netfilter entirely and the
> missing rule costs nothing. `iptables -t nat -S POSTROUTING` will confirm there is no rule matching
> your range, and the ping will work regardless — which is a good demonstration that **a NAT you cannot
> see in the tables is still a NAT**.
>
> Check which environment you have:
>
> ```bash
> ip rule show | grep -q 'lookup 2' && echo "policy-routed uplink — probably Docker Desktop's VM"
> ```
>
> On a real Linux host the packet leaves with `10.50.0.2` as its source and the `tcpdump` below shows
> it. On Docker Desktop, do the `tcpdump` anyway and read what the source has become — it is the same
> lesson arriving as an answer rather than a question. The
> [two-machines appendix](../act-6-control-plane/09-two-machines-from-nothing.md) is where this drill
> reproduces properly, because those are real machines.

**Reproduce it** (run; don't read):

```bash
UPLINK=$(ip route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
ip netns add app
ip link add veth-h type veth peer name veth-a
ip link set veth-a netns app
ip addr add 10.50.0.1/24 dev veth-h
ip link set veth-h up
ip netns exec app ip addr add 10.50.0.2/24 dev veth-a
ip netns exec app ip link set veth-a up
ip netns exec app ip link set lo up
ip netns exec app ip route add default via 10.50.0.1
sysctl -qw net.ipv4.ip_forward=1
```

> **`ip route get`, not `ip route show default` — and this is the fix for a real trap.** `show`
> reads only the **main** routing table, and on some hosts (Docker Desktop's VM among them) the
> default route lives in a separate policy-routing table instead, so `ip route show default` prints
> **nothing at all** and every `$(...)` built on it silently becomes an empty string — which then
> produces a command with a missing argument rather than an error you can read.
> `ip route get <dst>` asks the kernel which route it would *actually* use, whichever table holds
> it. [Act II lesson 01](../act-2-two-machines/01-ethernet-and-arp.md) is where this is explained;
> `ip rule show` is how you see the table it was hiding in.

**Confirm the symptom:**

```bash
ip netns exec app ping -c1 -W2 10.50.0.1 && echo "gateway (host): OK"
ip netns exec app ping -c1 -W2 8.8.8.8   || echo "internet: FAILED"
```

The namespace reaches its gateway on the wire, forwarding is enabled — yet the internet ping fails.

**Your move.** The cable works (the gateway ping proves it) and the kernel is forwarding, so the
request *is* leaving the namespace. Sniff the uplink and watch what source address the packet carries
onto the real wire — then ask which table was supposed to fix that, and whether its rule exists.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Watch what actually leaves the box:

```bash
UPLINK=${UPLINK:-$(ip route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')}   # re-derive it if this is a new shell
echo "uplink is: $UPLINK"                                        # must not be empty
tcpdump -ni "$UPLINK" icmp &
ip netns exec app ping -c1 8.8.8.8
```

```
IP 10.50.0.2 > 8.8.8.8: ICMP echo request ...
```

The packet leaves the host still carrying its **private source `10.50.0.2`** — an address the internet
has never heard of and can never route a reply back to. The request goes; the reply has nowhere to
come home to. Now read the table that was supposed to rewrite that source (lesson 3):

```bash
iptables -t nat -L POSTROUTING -n -v
```

There is **no `MASQUERADE`/`SNAT`** rule matching `10.50.0.0/24`. Nothing swaps the container's private
source for the host's routable IP on the way out, so `conntrack` has no mapping to reverse and the reply
never appears.

**Root cause:** missing source NAT (lesson 3). Forwarding moves the packet, but without MASQUERADE the
private source leaks onto the public wire. **Fix:**

```bash
iptables -t nat -A POSTROUTING -s 10.50.0.0/24 -o "$UPLINK" -j MASQUERADE
ip netns exec app ping -c1 8.8.8.8      # now replies arrive
```

This is line-for-line the rule Docker writes for `docker0` and kube-proxy's node-egress path — the one
`MASQUERADE` that lets every container on a box reach the internet.

**Cleanup:**
```bash
kill %1 2>/dev/null
iptables -t nat -D POSTROUTING -s 10.50.0.0/24 -o "$UPLINK" -j MASQUERADE 2>/dev/null
ip netns del app
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 1 "the rule that should have rewritten the source"
```

---

## Drill 2 — "Two containers on the same host can't reach each other"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Two namespaces are plugged into the same bridge, both have addresses in the same subnet,
> both interfaces show `UP` inside their namespace. But ns1 can't ping ns2 — no route error, it just
> times out. It's one switch and two cables; how is this not the simplest thing in the world?"*

**Reproduce it** (run; don't read):

```bash
ip netns add ns1
ip netns add ns2
ip link add br0 type bridge
ip link set br0 up
ip link add veth-a type veth peer name veth-a-c
ip link add veth-b type veth peer name veth-b-c
ip link set veth-a master br0
ip link set veth-b master br0
ip link set veth-a up
ip link set veth-a-c netns ns1
ip link set veth-b-c netns ns2
ip netns exec ns1 ip addr add 10.60.0.1/24 dev veth-a-c
ip netns exec ns2 ip addr add 10.60.0.2/24 dev veth-b-c
ip netns exec ns1 ip link set veth-a-c up
ip netns exec ns2 ip link set veth-b-c up
```

**Confirm the symptom:**

```bash
ip netns exec ns1 ip -br addr show veth-a-c     # UP, 10.60.0.1
ip netns exec ns2 ip -br addr show veth-b-c     # UP, 10.60.0.2
ip netns exec ns1 ping -c1 -W2 10.60.0.2 || echo "ns1 -> ns2: FAILED"
```

Both endpoints are up with the right addresses, on the same `/24` — and the ping still fails.

**Your move.** The addresses are right and the namespace-side interfaces are up, so this isn't IP and
isn't routing — the two are on one Layer-2 switch. A bridge only forwards a frame out a port that is
itself **up**. Every cable has two ends; you checked the ends *inside* the namespaces. Which ends
didn't you check?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Look at the *host-side* ends — the bridge's own ports:

```bash
ip -br link show veth-a        # host end of ns1's cable — UP
ip -br link show veth-b        # host end of ns2's cable — DOWN  ⟵
bridge link                    # veth-b listed, state disabled
```

The reproduce block brought up `veth-a` but **never brought up `veth-b`**. A veth is a cable with two
ends (lesson 2): the namespace end `veth-b-c` is up, but its partner `veth-b` — the port plugged into
the bridge — is down. The bridge will not forward a frame out a port that isn't up, so ns1's ARP for
`10.60.0.2` reaches the switch and dies there. The `fdb` confirms the bridge never learned ns2:

```bash
bridge fdb show br br0         # no entry pointing at veth-b
```

**Root cause:** one end of the cable left `DOWN` (lesson 2). The misleading part is that the
namespace's *own* view looks perfectly healthy — the fault is a port on the host side. **Fix:**

```bash
ip link set veth-b up
ip netns exec ns1 ping -c1 10.60.0.2       # now replies
bridge fdb show br br0                       # and the bridge has now learned both MACs
```

**Cleanup:**
```bash
ip netns del ns1; ip netns del ns2; ip link del br0
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 2 "the state of the thing between them"
```

---

## Drill 3 — "The published service answers inside the container but nowhere else"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"The app is definitely running — `exec` into the container and `curl localhost:8080`
> returns 200 every time. But hitting the same port from the host gets `connection refused`. We didn't
> change the app. It's like the port publish just… didn't."*

**Reproduce it** (run; don't read):

```bash
ip netns add app
ip link add veth-h type veth peer name veth-a
ip link set veth-a netns app
ip addr add 10.70.0.1/24 dev veth-h
ip link set veth-h up
ip netns exec app ip addr add 10.70.0.2/24 dev veth-a
ip netns exec app ip link set veth-a up
ip netns exec app ip link set lo up
ip netns exec app python3 -m http.server 8080 --bind 0.0.0.0 >/tmp/app.log 2>&1 &
sleep 1
```

**Confirm the symptom:**

```bash
ip netns exec app curl -s -o /dev/null -w 'inside the ns -> %{http_code}\n' 10.70.0.2:8080
curl -s -o /dev/null -w 'from the host -> %{http_code}\n' --max-time 2 10.70.0.1:8080 \
  || echo 'from the host -> connection refused'
```

Inside the namespace the server answers `200`; from the host, the same port is refused.

**Your move.** The listener is real — it answered its own namespace. The refusal from the host is the
tell: *nobody on the host is listening on 8080, and nothing redirects a host-bound packet into the
namespace.* Which one command shows what the host itself has bound? And which table is supposed to
carry a host-port knock across the wall into the container?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

First, prove the host has no listener — the server lives in another namespace, invisible to a
host-local connect:

```bash
ss -tlnp | grep 8080 || echo "nothing on the HOST is bound to 8080"
```

The socket table the host can see is empty on 8080; the `python3` listener sits in the `app`
namespace's *own* socket table. A container port becomes reachable from outside only when a **DNAT**
rule rewrites the destination and sends the packet across (lesson 3) — exactly what `docker run -p
8080:8080` installs. Read the NAT table and it isn't there:

```bash
iptables -t nat -L OUTPUT -n -v        # no DNAT for dpt 8080
iptables -t nat -L PREROUTING -n -v    # nor here
```

**Root cause:** the port publish (a DNAT rule) is missing — the classic "`-p` never happened" (lesson
3). **Fix** — send host-originated traffic for `10.70.0.1:8080` on into the container:

```bash
iptables -t nat -A OUTPUT -p tcp -d 10.70.0.1 --dport 8080 -j DNAT --to-destination 10.70.0.2:8080
curl -s -o /dev/null -w 'from the host -> %{http_code}\n' 10.70.0.1:8080     # now 200
```

The reply finds its way back with no return rule, because `conntrack` recorded the rewrite when the
first packet crossed (lesson 3) — the same reason a Kubernetes Service answers in both directions from
a single DNAT rule.

**Cleanup:**
```bash
iptables -t nat -D OUTPUT -p tcp -d 10.70.0.1 --dport 8080 -j DNAT --to-destination 10.70.0.2:8080 2>/dev/null
pkill -f 'http.server 8080'; ip netns del app
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 3 "the rewrite that never happened"
```

---

## Drill 4 — "Small requests are fine, big responses hang forever"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Two namespaces, one cable, both ends up, both addresses in the same `/24` — and `ping`
> works. Small requests come back instantly. Anything that returns a big payload hangs until the client
> gives up. There is no error anywhere: nothing in the app log, no ICMP, no `unreachable`. Retrying
> changes nothing. It's the same cable the working requests go over."*

**Reproduce it** (run; don't read):

```bash
ip netns add mtu1
ip netns add mtu2
ip link add veth-m1 type veth peer name veth-m2
ip link set veth-m1 netns mtu1
ip link set veth-m2 netns mtu2
ip netns exec mtu1 ip addr add 10.80.0.1/24 dev veth-m1
ip netns exec mtu2 ip addr add 10.80.0.2/24 dev veth-m2
ip netns exec mtu1 ip link set veth-m1 up
ip netns exec mtu2 ip link set veth-m2 up
ip netns exec mtu2 ip link set veth-m2 mtu 1400
```

**Confirm the symptom:**

```bash
ip netns exec mtu1 ping -c1 -W2 10.80.0.2         && echo "small packets: OK"
ip netns exec mtu1 ping -c1 -W2 -s 1450 10.80.0.2 || echo "large packets: FAILED, silently"
```

The small ping replies. The large one produces no reply and no error at all.

**Your move.** Reachability is not the question — the small ping settled that. The only thing that
changed between the packet that arrived and the packet that didn't is its *size*. So find the one number
on an interface that a 64-byte ping never exercises and a 1450-byte one does. Then work out which side
of the wire the packet actually died on, and prove it by watching the sender's interface and the
receiver's drop counters at the same time.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Read that number on both interfaces:

```bash
ip netns exec mtu1 ip link show veth-m1     # mtu 1500
ip netns exec mtu2 ip link show veth-m2     # mtu 1400  ⟵ smaller
```

The sending side accepts a 1500-byte frame, so its kernel has nothing to object to — the packet is
perfectly legal *where it is created*, which is why no error ever appears there. It becomes illegal only
on arrival, and the receiving end discards any frame bigger than its own MTU before that frame is ever a
packet: at the link layer, beneath the layer that would generate an ICMP error. Nobody is told. Watch
both halves of that:

```bash
ip netns exec mtu1 tcpdump -ni veth-m1 -c 1 icmp &     # the sender's own wire
sleep 1
ip netns exec mtu1 ping -c1 -W2 -s 1450 10.80.0.2      # request goes out; no reply ever returns
ip netns exec mtu2 ip -s link show veth-m2             # RX … dropped, climbing
```

The request leaves. It is counted as dropped on the far side. Nothing in between says a word — this is
the black hole from [Act II's MTU lesson](../act-2-two-machines/03b-mtu-and-fragmentation.md), reproduced
on plumbing you built yourself.

**Root cause:** an MTU mismatch across one link (Act II's MTU, lesson 2's veth). **Fix** — make the path
agree. Either raise the small end:

```bash
ip netns exec mtu2 ip link set veth-m2 mtu 1500
ip netns exec mtu1 ping -c1 -s 1450 10.80.0.2      # replies now
```

— or, when the small link is not yours to raise (a VPN, a cloud interconnect, an overlay's underlay),
lower the *sending* interface instead. That is precisely what
[Overlay and VXLAN](04-overlay-vxlan.md) does when it sets a tunnel's MTU to the path's smallest MTU
minus the encapsulation overhead. In a cluster, that one number decides whether large Pod-to-Pod
responses arrive at all.

**Cleanup:**
```bash
kill %1 2>/dev/null
ip netns del mtu1; ip netns del mtu2
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 4 "the property the two ends disagreed about"
```

---

## Drill 5 — "The container isn't as isolated as the networking drills assumed"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We built a container straight off a bundle, the way [lesson 05](05-who-does-this-for-you.md)
> showed — no Docker, just `runc`. It's running: the cgroup exists, `runc exec` reaches it, the process is
> alive. But someone testing it noticed it can see and use interfaces on the real network — traffic meant
> for the host itself shows up inside the container's own capture. Nothing about the build looked wrong.
> Where would that even come from?"*

**Reproduce it** (run; don't read):

```bash
apk add --no-cache runc skopeo umoci jq >/dev/null 2>&1
mkdir -p /work && cd /work
skopeo copy docker://alpine:latest oci:alpine-oci:latest >/dev/null 2>&1
umoci unpack --image alpine-oci:latest bundle >/dev/null 2>&1
jq '.process.terminal=false | .process.args=["/bin/sleep","300"] |
    .linux.namespaces = [.linux.namespaces[] | select(.type != "network")]' \
    bundle/config.json > /tmp/c.json && mv /tmp/c.json bundle/config.json
runc run -d -b bundle --pid-file /work/pid.txt drillbox
```

**Confirm the symptom:**

```bash
PID=$(cat /work/pid.txt)
ls -la /proc/$PID/ns/net
ls -la /proc/self/ns/net
```

```
lrwxrwxrwx    1 root     root             0 Aug 30 04:57 /proc/562/ns/net -> net:[4026531833]
lrwxrwxrwx    1 root     root             0 Aug 30 04:57 /proc/self/ns/net -> net:[4026531833]
```

Same inode. Whatever `runc run` just built, it is not privately networked the way
[lesson 05](05-who-does-this-for-you.md)'s own container was — and `runc list` still shows `drillbox`
running, cgroup and all, with no complaint anywhere.

**Your move.** You already own the one document that decides which namespaces a container gets, and you
already know which key in it to read. Read it here, and count its entries against the five
[lesson 05](05-who-does-this-for-you.md) showed you.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
jq '.linux.namespaces' /work/bundle/config.json
```

```json
[
  { "type": "pid" },
  { "type": "ipc" },
  { "type": "uts" },
  { "type": "mount" }
]
```

Four entries, not five. **`network` is missing.** `runc` did not skip isolating the network by accident
or by some fallback rule — it isolated exactly what `config.json` told it to, and nobody told it to
unshare a network namespace. `runc` has no opinion of its own about what "a container" needs; the
document is the whole contract, and an omission in it is an omission in the container, silently, with no
error at any point in the build or the run.

**Root cause:** `config.json`'s `linux.namespaces` array never had a `network` entry (lesson 05).
**Fix:**

```bash
runc delete -f drillbox
jq '.linux.namespaces += [{"type":"network"}]' /work/bundle/config.json > /tmp/c2.json \
  && mv /tmp/c2.json /work/bundle/config.json
runc run -d -b /work/bundle --pid-file /work/pid.txt drillbox
PID=$(cat /work/pid.txt)
ls -la /proc/$PID/ns/net       # now a different inode from /proc/self
```

This is the same fact lesson 05 built forward — declared, not implied — read here backward, from a
container that was missing one line and never once complained about it.

**Cleanup:**
```bash
runc delete -f drillbox 2>/dev/null
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 5 "the missing entry in config.json"
```

---

## Drill 6 — "`ctr` works, `crictl` doesn't, and nobody touched `crictl`"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Same containerd, same socket, same node. One engineer's `ctr images ls` works fine. The
> kubelet's own client, `crictl`, can't do anything on that node — not list, not version, nothing. It
> isn't a typo in the command; the connection itself is refused by something. What could possibly be
> different between two tools pointed at the exact same daemon?"*

**Reproduce it** (run; don't read):

```bash
apk add --no-cache containerd containerd-ctr cri-tools >/dev/null 2>&1
mkdir -p /etc/containerd
cat > /etc/containerd/config.toml <<'EOF'
version = 2
disabled_plugins = ["io.containerd.grpc.v1.cri"]
EOF
pkill containerd 2>/dev/null; sleep 1
containerd -c /etc/containerd/config.toml >/tmp/containerd.log 2>&1 &
sleep 2
```

**Confirm the symptom:**

```bash
ctr version >/dev/null && echo "ctr: OK, talking to containerd fine"
crictl version
```

```
ctr: OK, talking to containerd fine
ERRO[0000] validate service connection: validate CRI v1 runtime API for endpoint
"unix:///run/containerd/containerd.sock": rpc error: code = Unimplemented desc = unknown
service runtime.v1.RuntimeService
```

Read that error before touching anything. It is **not** "connection refused" and it is **not** "no such
file" — the socket is there and something answers on it. What comes back is `Unimplemented`: a request
for a *service* that this endpoint has never heard of.

**Your move.** [Lesson 06](06-the-kubelets-side.md) told you `crictl` and `ctr` are two independent
clients — but of what, exactly, on the daemon's side? `ctr` just proved the daemon itself is alive and
answering. If the same socket can be reachable for one client and answer "no such service" for another,
what does that say about how many separate things this one daemon can be serving over one door?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
cat /etc/containerd/config.toml
```

```
version = 2
disabled_plugins = ["io.containerd.grpc.v1.cri"]
```

`containerd` is not one API — it's a daemon built out of **plugins**, and the CRI service `crictl` needs
is one of them, not the core. `ctr` talks to containerd's own native API, which this daemon still serves
fine. `crictl` talks to the separate `RuntimeService`/`ImageService` pair
[lesson 06](06-the-kubelets-side.md) named — and this daemon was started with that specific plugin
switched off. The socket is real, containerd is up, and the one gRPC service `crictl` needs simply was
never registered on it. That is exactly why the error reads `Unimplemented` rather than any kind of
connection failure: the door is open, the room behind it doesn't exist.

**Root cause:** containerd's CRI plugin (`io.containerd.grpc.v1.cri`) was disabled at startup (lesson
06). **Fix:**

```bash
pkill containerd; sleep 1
rm -f /etc/containerd/config.toml
containerd >/tmp/containerd2.log 2>&1 &
sleep 2
crictl version      # now answers
```

This is the real-world version of a bug that has taken down more than one cluster: a hand-rolled
`containerd` config that disables `cri` for an unrelated reason (usually chasing a different plugin)
leaves every `ctr`-based health check green while the kubelet — which only ever speaks CRI — cannot
run a single Pod.

**Cleanup:**
```bash
pkill containerd 2>/dev/null
rm -f /etc/containerd/config.toml
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 6 "the plugin that was switched off"
```

---

## Drill 7 — "The fix for the leaked secret closed the ticket. Did it fix anything?"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Security flagged the build from [lesson 07](07-how-a-layer-is-made.md) — a secret
> written in one layer was still recoverable from an earlier one, even though a later `RUN` deleted it.
> A teammate's fix: overwrite the file with zeros before deleting it, in that same step, so there's
> nothing readable left to recover. The build log shows nothing unusual, so they closed the ticket.
> Did it actually fix anything?"*

**Reproduce it** (run; don't read):

```bash
apk add --no-cache buildkit buildctl >/dev/null 2>&1
pkill buildkitd 2>/dev/null; sleep 1
buildkitd >/tmp/buildkitd.log 2>&1 &
sleep 2
mkdir -p /work/build7 && cd /work/build7
cat > Dockerfile <<'EOF'
FROM alpine:latest
RUN echo "hunter2" > /secret.txt
RUN dd if=/dev/zero of=/secret.txt bs=1 count=7 conv=notrunc && rm /secret.txt
CMD ["cat", "/etc/os-release"]
EOF
buildctl build --frontend dockerfile.v0 --local context=. --local dockerfile=. \
  --output type=oci,dest=out.tar >/tmp/build.log 2>&1
mkdir -p out && tar -xf out.tar -C out
```

**Confirm what "fixed" looked like:**

```bash
grep -c '^#[0-9]' /tmp/build.log && echo "the build ran clean — nothing flagged, nothing errored"
```

That log is all the teammate checked, and it tells you nothing about whether the bytes still exist
anywhere — which is exactly [lesson 07](07-how-a-layer-is-made.md)'s own point about a running
container's filesystem, one level removed: a clean build log isn't runtime evidence either.

**Your move.** You already know how to open a raw layer instead of trusting a log or a running
container. `dd`-ing zeros over the file happens in the *same* `RUN` as the `rm` — before you look, decide
whether you expect that to change which layer the original bytes live in at all.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Walk the manifest to find the two layers this Dockerfile produced, in order:

```bash
cd /work/build7/out
M=$(jq -r '.manifests[0].digest' index.json | sed 's/sha256://')
jq -r '.layers[].digest' "blobs/sha256/$M" | sed 's/sha256://'
```

Take the second and third lines — the write layer and the delete layer — and open each raw tar:

```bash
tar -xzOf blobs/sha256/<the-write-layer> secret.txt
tar -tzvf blobs/sha256/<the-delete-layer>
```

```
hunter2
---------- 0/0         0 1970-01-01 00:00:00 .wh.secret.txt
```

**The write layer still holds the literal string `hunter2`, untouched.** The zero-and-delete step
changed nothing about it, because a Dockerfile layer is the *net* filesystem diff at the end of one
`RUN` — not a recording of every command that ran inside it. Overwriting the file and then removing it,
in the same step, still ends that step with the file simply gone, so BuildKit writes exactly the one
whiteout `rm` alone would have written. The zeroing was real work that produced a real intermediate
state — and that state never became a layer, because nothing asked for it to. Layers are immutable and
strictly additive: no later `RUN`, whatever it does, can reach back and rewrite the bytes an earlier
layer already committed.

**Root cause:** believing a later `RUN` can retroactively change an earlier layer's already-shipped
bytes (lesson 07, one step further). **The actual fix** is not "wipe it before deleting it" — it's never
letting the secret enter a committed layer in the first place. BuildKit has a real mechanism for that:

```bash
cat > Dockerfile.fixed <<'EOF'
# syntax=docker/dockerfile:1
FROM alpine:latest
RUN --mount=type=secret,id=mysecret cat /run/secrets/mysecret > /dev/null
CMD ["cat", "/etc/os-release"]
EOF
echo -n "hunter2" > /tmp/mysecret.txt
buildctl build --frontend dockerfile.v0 --local context=. --local dockerfile=. \
  --opt filename=Dockerfile.fixed --secret id=mysecret,src=/tmp/mysecret.txt \
  --output type=oci,dest=outfixed.tar
mkdir -p outfixed && tar -xf outfixed.tar -C outfixed
for f in outfixed/blobs/sha256/*; do gunzip -c "$f" 2>/dev/null | grep -a hunter2; done
echo "(no output above — the secret was never in any layer to begin with)"
```

`--mount=type=secret` makes the secret available only inside the running build step, on a mount that is
never part of the snapshot BuildKit diffs to produce a layer. There is no delete step to forget, because
there is no layer to leak from.

**Cleanup:**
```bash
pkill buildkitd 2>/dev/null
rm -rf /work/build7
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 7 "what a later RUN can never do to an earlier layer"
```

---

## Drill 8 — "The runbook's first command says the namespace does not exist"

**Target: 4 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Container's up, app inside it is misbehaving, and I want to see its interfaces. Our
> runbook says `ip netns exec <container> ip addr`. It tells me the namespace does not exist. So I
> listed the namespaces on the box and got **nothing** — on a machine that is definitely running
> containers. Is the container's networking gone, or is this box broken?"*

**Reproduce it** (run; don't read):

```bash
apk add --no-cache runc skopeo umoci jq >/dev/null 2>&1
mkdir -p /work && cd /work
skopeo copy docker://alpine:latest oci:alpine-oci:latest >/dev/null 2>&1
umoci unpack --image alpine-oci:latest bundle >/dev/null 2>&1
jq '.process.terminal=false | .process.args=["/bin/sleep","600"]' bundle/config.json \
  > /tmp/c.json && mv /tmp/c.json bundle/config.json
rm -rf /var/run/netns
runc run -d -b bundle --pid-file /work/pid.txt drillbox
```

**Confirm the symptom:**

```bash
runc list
ip netns exec drillbox ip addr; echo "(exit=$?)"
ip netns list; echo "(exit=$?)"
```

```
ID          PID    STATUS     BUNDLE         CREATED
drillbox    55     running    /work/bundle   2026-08-31T01:16:50Z

Cannot open network namespace "drillbox": No such file or directory
(exit=255)

(exit=0)
```

Read the two exit codes against each other, because they are the whole drill. One command **fails
loudly** on a name. The other **succeeds silently** on a list. And `runc list` says the container is
running.

**Your move.** Do not go looking for what deleted the namespace. Decide first whether anything is
broken at all — you have a tool that proves a namespace's identity, and you have the container's PID.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Nothing is broken. Prove the namespace exists before you touch anything:

```bash
PID=$(cat /work/pid.txt)
readlink /proc/$PID/ns/net
readlink /proc/self/ns/net
ls -la /var/run/netns/
```

```
net:[4026533147]
net:[4026531833]
ls: /var/run/netns/: No such file or directory
```

Two different inodes, so the container has its own network namespace, exactly as
[lesson 05](05-who-does-this-for-you.md) built it. And `/var/run/netns/` — the directory `ip netns`
reads — does not exist.

**Root cause:** `ip netns` only ever sees namespaces that have a **name**, and a name is a bind mount
under `/var/run/netns/` that `ip netns add` creates. No container runtime creates one, so `ip netns
list` reports nothing and exits 0 — an empty list, correctly listed. The runbook was written against
namespaces somebody had made by hand ([lesson 05b](05b-entering-what-you-did-not-name.md)).

**Fix** — either give it the name the runbook expects:

```bash
PID=$(cat /work/pid.txt)
mkdir -p /var/run/netns
ln -sf /proc/$PID/ns/net /var/run/netns/drillbox
ip netns list                                    # drillbox
ip netns exec drillbox ip -o addr show           # lo, and only lo
```

or skip the name, which is what the runbook should say:

```bash
nsenter -t $PID -n ip -o addr show
```

Both return `lo 127.0.0.1/8` and nothing else — which is not a second fault. `runc` created an empty
network namespace because `config.json` asked for one and nothing asked for a veth; the wiring in
[lesson 02](02-veth-and-bridge.md) is what `docker run` adds on top.

**Cleanup:**
```bash
runc delete -f drillbox 2>/dev/null; rm -f /var/run/netns/drillbox
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 8 "ip netns only sees named namespaces"
```

*(The verifier checks that the runbook's own command works, so make the name even if `nsenter` is what
you would reach for on a real node — it also checks the PID route, and that you left the container
running.)*

---

## Drill 9 — "It has every capability there is and cannot create a file"

**Target: 6 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Our agent runs as root and writes `/etc/agent.log`. It is logging permission-denied on
> that path. I checked the obvious thing — `ps` says the process is UID 1000, not root, so somebody
> broke the unit. Except the agent's own startup line says `uid=0`, and the capability field in
> `/proc` is the fullest I have ever seen. Three tools, three answers. Which one is lying?"*

**Reproduce it** (run; don't read):

```bash
rm -f /tmp/agent.pid /tmp/agent.err /tmp/agent.log /etc/agent.log
chmod 1777 /tmp
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -U --map-root-user sh -c '
  echo $$ > /tmp/agent.pid
  echo "starting as uid=$(id -u)" > /tmp/agent.log
  while :; do (echo tick >> /etc/agent.log) 2>>/tmp/agent.err; sleep 3; done' &
sleep 4
```

**Confirm the symptom:**

```bash
PID=$(cat /tmp/agent.pid)
cat /tmp/agent.log
tail -1 /tmp/agent.err
grep -E '^(Uid|CapEff):' /proc/$PID/status
```

```
starting as uid=0
sh: can't create /etc/agent.log: Permission denied
Uid:	1000	1000	1000	1000
CapEff:	000001ffffffffff
```

**Three tools, three answers, and none of them is wrong.** The agent says it is root. `/proc` says it
is 1000. `CapEff` says it holds every capability the kernel has — and it cannot create a file in a
directory that is `drwxr-xr-x root root`.

**Your move.** Do not change the agent and do not `chmod` anything yet. There is one file in `/proc`
that reconciles all three readings, and Act IV taught you to read `/proc/<pid>/` for exactly this kind
of disagreement.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
PID=$(cat /tmp/agent.pid)
cat /proc/$PID/uid_map
```

```
         0       1000          1
```

`<inside> <outside> <range>`: **UID 0 inside this process's user namespace is UID 1000 on the host.**
Every reading was true of a different vantage point. `id -u` reads the map and says 0. `/proc/<pid>/status`
is being read by *you*, from outside, and reports the host UID. And the capabilities are real — they are
just evaluated against that map, so they buy nothing over files owned by UIDs the map cannot name
([lesson 05c](05c-who-am-i.md)).

**Root cause:** the agent runs in a user namespace whose map is `0 1000 1`. It is root over one UID and
nobody over every other, and `/etc` belongs to a UID it cannot name — so the refusal is ordinary file
permission against host UID 1000, not a missing privilege.

**Fix** — act on the UID the map *points at*, never the one the process reports:

```bash
install -o 1000 -g 1000 -m 644 /dev/null /etc/agent.log
sleep 4
wc -l < /etc/agent.log          # growing
ls -ln /etc/agent.log           # 1000 1000
```

And the confirmation worth keeping, from the agent's own side of the map:

```bash
PID=$(cat /tmp/agent.pid)
nsenter -t $PID -U --preserve-credentials sh -c 'ls -ln /etc/agent.log' 2>/dev/null
```

```
-rw-r--r--    1 0        0                5 /etc/agent.log
```

`1000 1000` from outside, `0 0` from inside. **One file, one inode, two owners** — and the agent needed
no new privilege, only a file whose owner it could name.

Note which fix you did *not* apply: `chown 0 /etc/agent.log` would have made it unwritable again, because
UID 0 outside is not in that map at all. Chasing the UID the process reports is the trap.

**Cleanup:**
```bash
pkill -f 'while :; do' 2>/dev/null
rm -f /tmp/agent.pid /tmp/agent.err /tmp/agent.log /etc/agent.log
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-4 9 "the process is in a user namespace with a mapped uid"
```

---

## Where this leaves you

Nine failures, nine primitives, one method: meet a bare symptom, decide *which* piece of hand-built
plumbing — or hand-built container, or hand-written spec document — is missing, misconfigured, or simply
misunderstood — or, twice, decide that **nothing is broken and a tool is answering a narrower question
than the ticket assumed** — and read the one file, rule, or raw byte that proves it. A private source escaping onto
the wire because no `MASQUERADE` caught it. A bridge port left down so frames die at the switch. A
published port that was never a DNAT rule at all. A link whose size nobody agreed on, which fails only
for packets big enough to matter. A container with one line missing from the document that is its whole
contract, silently short of the isolation everyone assumed it had. A daemon serving one client and
silently refusing another, because the two were never talking to the same plugin. A "fix" that changed
nothing, because no later step can rewrite a layer already shipped. A namespace that was never missing,
listed by a tool that only ever knew about the ones somebody had named by hand. A process holding all
forty-one capabilities and unable to create a file, because the number it calls itself and the number
the host bills it as are two ends of one three-integer map. Nobody told you which idea applied;
you ranged across the whole act to find it. Every one of these is a bug you will meet again wearing a
Kubernetes name — a node that can't egress, a Pod unreachable on its node, a Service that resolves but
never answers, an overlay that delivers health checks and swallows real responses, a Pod stuck because
its runtime config was wrong in one field, a kubelet that can't create a single sandbox because the
container runtime it's calling never loaded the service it needed, an image whose layers say more than
its last `docker history` line ever let on.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Act V — Kubernetes](../act-5-kubernetes/README.md)** →
