# Act III — The Internet

In 1974, Vint Cerf and Bob Kahn published *A Protocol for Packet Network Intercommunication*. The networks they were trying to glue together — ARPAnet, packet radio, satellite links — were not just different kinds of wire; they were unreliable in different ways. A radio link drops packets in a thunderstorm. A satellite hop reorders them. A congested router, faced with more packets than it can hold, simply throws some away and feels no remorse.

The tempting fix was to make every router reliable: have each one remember what it forwarded, retransmit on loss, keep everything in order. Cerf and Kahn made the opposite bet, and it is the single most important design decision in the history of the network.

They declared the network unreliable *by design*. Routers would be allowed to drop, reorder, and duplicate freely, and would be kept dumb and fast. All the work of making a conversation reliable would be pushed to the two endpoints — the two machines actually talking. This is the end-to-end principle, and it is why the internet could grow: a new kind of link could join without understanding anything about reliability, because reliability was never the link's job. It was the endpoints' job. And that job is what we call TCP.

So Act III is the act where two processes on two machines, separated by an ocean of routers that owe them nothing, manage to behave as if they were in the same room — one calls `write()`, the other calls `read()`, and the bytes arrive whole and in order.

We will build that illusion in the order the kernel does. First the agreement that starts every conversation: the three-way handshake, and why the starting numbers are random (a story that runs through the 1988 Morris worm).

Then the truth that a connection is not a thing but a *state* the kernel tracks — a state machine you can read row by row in `/proc/net/tcp` — including the strangest state of all, `TIME_WAIT`, a connection guarding against ghosts of a connection already dead. Then the table next door: `conntrack`, the kernel's memory of who is talking to whom, which exists because a machine in the middle of someone else's conversation has to remember what it rewrote. Kubernetes lives and dies by that table, so we meet it early and flag it loudly.

Only then the reliability itself: acknowledgements, retransmission, and a sliding window of bytes in flight — and the two entirely different limits on that window, the receiver's ceiling and the sender's guess about a network that never tells it anything, which is why real throughput ramps, sawtooths, and backs off the way it does.

Then HTTP, a conversation written in plain text where a single blank line is load-bearing — and the chain of problems that drove it from one request per connection to HTTP/3 over UDP, plus the machines that sit in the middle and what each of them can see. And finally TLS, the lock we bolt onto the socket so the routers in the middle can carry our bytes without reading them.

After this act you will be able to take any HTTPS request that feels slow or broken, break it into DNS, TCP handshake, TLS handshake, and transfer, and say exactly which stage hurt — read the connection's life story directly out of the kernel's own files, and explain why its throughput behaved the way it did.

## The lessons — read in this order

Work through these in order. Each one runs experiments in the lab container and ends with a link to the next, so you never have to guess where to go.

1. **[The three-way handshake](01-tcp-handshake.md)** — how two sides agree, from scratch, where to start counting.
2. **[TCP states](02-tcp-states.md)** — the connection as a state machine you can read row by row, `TIME_WAIT` included.
3. **[conntrack — the kernel's flow table](02b-conntrack.md)** — what a machine in the middle of someone else's conversation has to remember.
4. **[TCP and reliability](03-tcp-reliability.md)** — the sliding window, and the two different limits on it: the receiver's ceiling and the network's.
5. **[HTTP](04-http.md)** — structure imposed on the byte stream, why the protocol kept being replaced, and what a proxy in the middle can see.
6. **[TLS](05-tls.md)** — the lock bolted onto the socket.

When you've finished all six, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *use* it under fire with the symptom-first **[Diagnose it →](diagnose.md)** on-call drills. When you want to look something up rather than learn it, that is what [the instrument panel](../../reference/README.md) is for — and [the grammar](../../reference/01-the-grammar.md) is the page that lets you work out a command nobody showed you.

## What breaks here

Everything in this act assumes one real machine per endpoint, holding one real IP address that is genuinely its own. The handshake works because the SYN goes to a machine that answers as itself. `conntrack` works because each connection has one honest source.

But a Kubernetes node runs hundreds of Pods, each believing it owns a private IP, all sharing a handful of real network interfaces — and a Service IP belongs to *no machine at all*. What happens when one machine must pretend to be many, and a single address must stand in for a crowd? That is Act IV.
