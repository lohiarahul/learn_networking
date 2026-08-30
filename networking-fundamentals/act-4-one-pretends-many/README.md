# Act IV — One machine pretends to be many

In 1967, IBM's CP-67 ran on a single System/360 mainframe in a room the size of a tennis court, and it did something that felt like a magic trick to everyone who used it: it gave each user what looked like their own private computer. You logged in and you had a whole machine — your own memory, your own disk, your own operating system to boot however you liked — except you didn't, because behind the curtain one physical machine was being sliced into many virtual ones, each isolated from the others, each convinced it was alone. The hardware was shared; the experience was private.

That idea — *one machine pretending to be many* — was the seed of everything we now call virtualization, and it took roughly forty years to fall from million-dollar mainframes into commodity Linux boxes. But when it finally did, a problem came with it that CP-67 never had to fully solve: if one machine now hosts dozens of isolated tenants, and every tenant wants to talk to the network, then the *network stack itself* has to be virtualized too. One kernel, many private networks.

This act is about how Linux does exactly that. We start from the deepest idea in the course — everything is a file, and a process has a private view of the world — and we take it one step further: we make the *network* private too. A **network namespace** is the process-isolation idea applied to the networking subsystem, and like everything else it turns out to be a file. Its twin, **cgroups**, answers a question a namespace never asks at all.

From there we build the plumbing by hand. We will create a virtual wire between two namespaces with a **veth pair**, plug several of them into a software switch with a **Linux bridge**, teach the kernel to rewrite addresses on the fly with **iptables and NAT** so a private container can reach the public internet — the `iptables` Act III named and deferred to here — and finally wrap a packet inside another packet with **VXLAN**, building a working tunnel between two namespaces so you can watch one private network ride inside another on a wire that has never heard of it.

After this act you will be able to take one bare Linux box and, from memory and first principles, carve it into multiple isolated networks, wire them together, give them internet access, and explain every packet's path by pointing at the file or kernel hook responsible. You will have built, by hand, the thing Kubernetes builds for you on every node — and you'll recognize it when you see it.

## The lessons — read in this order

Work through these in order. Each one runs experiments in the lab container and ends with a link to the next, so you never have to guess where to go.

1. **[Namespaces](01-namespaces.md)** — process isolation applied to the whole network stack.
2. **[cgroups](01b-cgroups.md)** — the other half of a container: not what it can see, but how much it can use.
3. **[veth and bridge](02-veth-and-bridge.md)** — the virtual wire and the software switch.
4. **[iptables and NAT](03-iptables-and-nat.md)** — rewriting addresses so a private host can reach the internet, and the nftables store both grammars actually write to.
5. **[Overlay and VXLAN](04-overlay-vxlan.md)** — wrapping a packet in a packet so two private networks share one wire.
6. **[Who does this for you](05-who-does-this-for-you.md)** — the OCI runtime spec, `runc`, and `containerd`: the same five namespaces and cgroup, built by a program instead of your fingers.

Every lesson ends by tearing down what it built, so you can work straight through in one container without tripping over the last experiment's leftovers.

When you've finished them all, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *use* it under fire with the symptom-first **[Diagnose it →](diagnose.md)** on-call drills. To find these same primitives running on your own machine — including the honest twist that none of them exist on macOS — read **[Act IV in the wild →](in-the-wild.md)**. When you want to look something up rather than learn it, that is what [the instrument panel](../../reference/README.md) is for — [the map](../../reference/03-the-map.md) ties every tool to the piece of kernel state it reads, and [the grammar](../../reference/01-the-grammar.md) is the page that lets you work out a command nobody showed you.

## What breaks here

Everything we build in this act lives on **one host** — including the tunnel, which we build between two namespaces because two namespaces on one kernel are enough to prove the mechanism. We can isolate, cap, wire, route, translate, and encapsulate, all by hand. But a real cluster runs Pods across hundreds of *actual* nodes, and the Pods come and go by the thousand, scheduled wherever there's room. Nobody is going to run these `ip` commands by hand a thousand times a second.

Something has to decide *which* Pod lands on *which* node, then automatically perform every step of this act — namespace, cgroup limits, veth, bridge, NAT, overlay — the instant a Pod is born, and tear it all down when the Pod dies. That something is Kubernetes, and that is Act V.

> **The question to carry forward:** we can virtualize one machine's network, cap what each tenant consumes, and connect namespaces on one host — so who finds a host with room, and who wires up the namespace, the veth, the route and the limits automatically, every single time, without ever being told twice?

