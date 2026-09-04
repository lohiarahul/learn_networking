# Act IV — One machine pretends to be many

In 1967, IBM's CP-67 ran on a single System/360 mainframe in a room the size of a tennis court, and it did something that felt like a magic trick to everyone who used it: it gave each user what looked like their own private computer. You logged in and you had a whole machine — your own memory, your own disk, your own operating system to boot however you liked — except you didn't, because behind the curtain one physical machine was being sliced into many virtual ones, each isolated from the others, each convinced it was alone. The hardware was shared; the experience was private.

That idea — *one machine pretending to be many* — was the seed of everything we now call virtualization, and it took roughly forty years to fall from million-dollar mainframes into commodity Linux boxes. But when it finally did, a problem came with it that CP-67 never had to fully solve: if one machine now hosts dozens of isolated tenants, and every tenant wants to talk to the network, then the *network stack itself* has to be virtualized too. One kernel, many private networks.

This act is about how Linux does exactly that. We start from the deepest idea in the course — everything is a file, and a process has a private view of the world — and we take it one step further: we make the *network* private too. A **network namespace** is the process-isolation idea applied to the networking subsystem, and like everything else it turns out to be a file. Its twin, **cgroups**, answers a question a namespace never asks at all.

From there we build the plumbing by hand. We will create a virtual wire between two namespaces with a **veth pair**, plug several of them into a software switch with a **Linux bridge**, then find the **five netfilter hooks** — the `iptables` Act III named and deferred to here — by watching a packet leave with an address nobody can reply to. From there we build a NAT gateway by hand, outbound and inbound, until `docker run -p 8080:80` is a rule we wrote ourselves; read a real ruleset written by somebody else and find our own firewall rule doing nothing at all; and then stay at those five hooks long enough to do the three jobs everyone actually reaches for them for: **a stateful firewall** that refuses everything by default, **NAT's real ceiling** and the tables that steer a packet rather than rewrite it, and **intercepting a connection that was never addressed to you** — and finally wrap a packet inside another packet with **VXLAN**, building a working tunnel between two namespaces so you can watch one private network ride inside another on a wire that has never heard of it.

After this act you will be able to take one bare Linux box and, from memory and first principles, carve it into multiple isolated networks, wire them together, give them internet access, and explain every packet's path by pointing at the file or kernel hook responsible. You will have built, by hand, the thing Kubernetes builds for you on every node — and you'll recognize it when you see it.

## The lessons — read in this order

Work through these in order. Each one runs experiments in the lab container and ends with a link to the next, so you never have to guess where to go.

1. **[Namespaces](01-namespaces.md)** — process isolation applied to the whole network stack.
2. **[cgroups](01b-cgroups.md)** — the other half of a container: not what it can see, but how much it can use.
3. **[veth and bridge](02-veth-and-bridge.md)** — the virtual wire and the software switch.
4. **[Docker networks](02b-docker-networks.md)** — why `docker0/brif/` is often empty on a machine full of running containers, and the naming quirk that hides a `kind` cluster's own bridge even harder.
5. **[iptables — the five hooks](03-iptables-and-nat.md)** — a namespace whose packets reach the internet's doorstep and die there, and the five places in the kernel where you are allowed to do something about it.
6. **[Publishing a port](03a-publishing-a-port.md)** — `MASQUERADE` outbound and `DNAT` inbound, built by hand: `docker run -p 8080:80` is two rules, and you will find out the hard way why it is two and not one.
7. **[Reading a ruleset you did not write](03b-reading-a-ruleset-you-did-not-write.md)** — your own `DROP` leaves a published port wide open, Docker's `FORWARD` chain turns out to be a four-level tree, and `iptables` reports the opposite of what the kernel will do.
8. **[The stateful firewall](03c-the-stateful-firewall.md)** — a default-deny policy breaks the machine that set it, and the one rule that fixes it matches on no port at all.
9. **[When NAT runs out](03d-when-nat-runs-out.md)** — `MASQUERADE` is an allocation, not a function: its ceiling, its collisions, and the two tables that neither filter nor translate.
10. **[The transparent proxy](03e-the-transparent-proxy.md)** — intercepting a connection that was never addressed to you, and recovering the destination your own rewrite destroyed.
11. **[Overlay and VXLAN](04-overlay-vxlan.md)** — wrapping a packet in a packet so two private networks share one wire.
12. **[Who does this for you](05-who-does-this-for-you.md)** — the OCI runtime spec, `runc`, and `containerd`: the five namespaces and cgroup a bundle asks for, built by a program instead of your fingers.
13. **[Entering what you did not name](05b-entering-what-you-did-not-name.md)** — `ip netns list` is empty on a machine full of containers, and exits 0. What a name actually is, and the tool that needs a PID instead of one.
14. **[Who am I](05c-who-am-i.md)** — the third question the act never posed. `/proc/self/uid_map`, an unprivileged user who becomes root, and a process holding all 41 capabilities that still cannot write to `/etc`.
15. **[The kubelet's side](06-the-kubelets-side.md)** — the Container Runtime Interface: why a Pod's sandbox is created before any container in it, proven by a network setup failing first.
16. **[How a layer is made](07-how-a-layer-is-made.md)** — the build side of Act I 06b's overlayfs read: BuildKit, and a secret you can recover from a raw layer after the `RUN` that deleted it.

Every lesson ends by tearing down what it built, so you can work straight through in one container without tripping over the last experiment's leftovers.

When you've finished them all, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *use* it under fire with the symptom-first **[Diagnose it →](diagnose.md)** on-call drills. To find these same primitives running on your own machine — including the honest twist that none of them exist on macOS — read **[Act IV in the wild →](in-the-wild.md)**. When you want to look something up rather than learn it, that is what [the instrument panel](../../reference/README.md) is for — [the map](../../reference/03-the-map.md) ties every tool to the piece of kernel state it reads, and [the grammar](../../reference/01-the-grammar.md) is the page that lets you work out a command nobody showed you.

## What breaks here

Everything we build in this act lives on **one host** — including the tunnel, which we build between two namespaces because two namespaces on one kernel are enough to prove the mechanism. We can isolate, cap, wire, route, translate, and encapsulate, all by hand. But a real cluster runs Pods across hundreds of *actual* nodes, and the Pods come and go by the thousand, scheduled wherever there's room. Nobody is going to run these `ip` commands by hand a thousand times a second.

Something has to decide *which* Pod lands on *which* node, then automatically perform every step of this act — namespace, cgroup limits, veth, bridge, NAT, overlay — the instant a Pod is born, and tear it all down when the Pod dies. That something is Kubernetes, and that is Act V.

> **The question to carry forward:** we can virtualize one machine's network, cap what each tenant consumes, and connect namespaces on one host — so who finds a host with room, and who wires up the namespace, the veth, the route and the limits automatically, every single time, without ever being told twice?

