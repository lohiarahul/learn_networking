# TCP states

You keep saying "a connection" as if it were an object — a wire, a pipe, a thing you could hold. It is not. There is no connection anywhere in the network. A TCP connection is a shared *belief*, maintained independently by two kernels, each holding a small record that says "I am in the middle of talking to that address, and I am currently in such-and-such a state." The connection exists only as long as both records agree. And those records are files you can read.

### Why does a connection need named states at all?

**Because a reliable conversation has steps that must happen in order, and a name is how the kernel remembers which step it is on.**

A reliable conversation over an unreliable network has moments that must be handled in a particular order: you cannot send data before agreeing on sequence numbers, you cannot declare a connection closed while the other side might still be sending, you cannot reuse a port while ghost packets from the last conversation might still be wandering the network. Each of these "you cannot yet" conditions is a question the kernel must remember the answer to.

Tracking that with ad-hoc flags is how you get a kernel that deadlocks or corrupts streams. The discipline that made TCP correct was to model the connection explicitly as a finite state machine, written down in RFC 793 — every connection is in exactly one named state, and every packet either causes a defined transition or is rejected.

### What are the states, and what is each one waiting for?

**Each state is a question the kernel is currently waiting to answer — which is why reading the state tells you what a stuck connection is stuck on.**

A connection is a state the kernel tracks, and you can read the state directly out of `/proc/net/tcp` (the `st` column). Don't memorize the table below — each state becomes obvious in the diagram and the experiment that follow.

| State | The question it is waiting to answer |
| --- | --- |
| `LISTEN` | "Is anyone trying to connect to me?" |
| `SYN_SENT` | "I sent a SYN; is the SYN-ACK coming?" |
| `SYN_RECV` | "I got a SYN and replied; is the final ACK coming?" |
| `ESTABLISHED` | "We agreed; we are exchanging data." |
| `FIN_WAIT_1` | "I sent a FIN to close my side; has it been acknowledged?" |
| `FIN_WAIT_2` | "My FIN was acknowledged; is the other side going to send *its* FIN?" |
| `TIME_WAIT` | "I've seen their FIN and acknowledged it; now I wait to be sure no stale packets from this connection are still in flight before I let this port be reused." |
| `CLOSE_WAIT` | "The other side closed first; the application still has my socket — am I done sending?" |
| `LAST_ACK` | "I sent my FIN after the other side closed; is the final ACK coming?" |

Reading the state tells you exactly what each side is waiting *for*, which is exactly what you need when a connection is stuck.

### What does the whole machine look like?

**Two spines: one for the side that closes first, one for the side that closes second — and only the first pays the `TIME_WAIT` tax.**

The full machine, with transitions labeled `event / action sent`:

*Read it as two stories: the left spine is the side that opens and then closes first (active), the right spine is the side that receives the connection and closes second (passive) — and whoever sends the first FIN is the one who pays the `TIME_WAIT` tax at the bottom.*

<!-- figure -->

```
                         ┌──────────┐
                         │  CLOSED  │◄───────────────────────┐
                         └────┬─────┘                        │
              passive open    │    active open: send SYN     │
                  (listen)    │                              │
                ┌─────────────┴──────────────┐               │
                ▼                             ▼               │
          ┌──────────┐                  ┌──────────┐         │
          │  LISTEN  │                  │ SYN_SENT │         │
          └────┬─────┘                  └────┬─────┘         │
   recv SYN /  │                             │ recv SYN-ACK /│
   send SYN-ACK│                             │ send ACK      │
                ▼                            │               │
          ┌──────────┐                       │               │
          │ SYN_RECV │                       │               │
          └────┬─────┘                       │               │
   recv ACK /  │                             │               │
        ─────  └──────────────┬──────────────┘               │
                              ▼                               │
                       ┌─────────────┐                        │
            ┌──────────┤ ESTABLISHED ├──────────┐             │
            │          └─────────────┘          │             │
   app close / send FIN          recv FIN / send ACK          │
            ▼                                   ▼             │
     ┌────────────┐                      ┌────────────┐       │
     │ FIN_WAIT_1 │                      │ CLOSE_WAIT │       │
     └─────┬──────┘                      └─────┬──────┘       │
  recv ACK │                       app close / │ send FIN     │
           ▼                                   ▼              │
     ┌────────────┐                      ┌────────────┐       │
     │ FIN_WAIT_2 │                      │  LAST_ACK  │       │
     └─────┬──────┘                      └─────┬──────┘       │
 recv FIN /│                            recv ACK│ ─────────────┘
 send ACK  ▼                                    │  (→ CLOSED)
     ┌────────────┐                             │
     │ TIME_WAIT  │   wait 2*MSL, then ─────────┘  (→ CLOSED)
     └────────────┘
```

The left spine is the side that closes *first* (the active closer); the right spine (`CLOSE_WAIT` → `LAST_ACK`) is the side that closes *second*. Whoever sends the first FIN pays for `TIME_WAIT`.

### Where do you read the state?

**The same `/proc/net/tcp` as before — the `st` column, as a two-digit hex code.**

Same table as before, read by state:

```
/proc/net/tcp     the st column is the state, as a hex code
```

The state codes: `01` ESTABLISHED, `02` SYN_SENT, `03` SYN_RECV, `04` FIN_WAIT1, `05` FIN_WAIT2, `06` TIME_WAIT, `07` CLOSE, `08` CLOSE_WAIT, `09` LAST_ACK, `0A` LISTEN.

So a row whose `st` field is `06` is a connection sitting in `TIME_WAIT`. The tool `ss -tan` reads this and prints the state by name; `ss -tan state time-wait` filters to just the `06` rows. It is decoding that hex column.

`TIME_WAIT` is the most surprising state, so dwell on it. When your side closes a connection first, after the final ACK you do *not* immediately destroy the record. You hold it in `TIME_WAIT` for twice the Maximum Segment Lifetime — on Linux roughly 60 seconds — refusing to reuse that exact four-tuple (local IP, local port, remote IP, remote port).

Why keep a dead connection around for a minute? Because a delayed duplicate packet from *this* connection might still be crawling through the network, and if you immediately opened a *new* connection on the same four-tuple, that ghost could be accepted as valid data for the new connection.

`TIME_WAIT` is the kernel protecting a connection that does not yet exist, against a packet from a connection that no longer exists. It is pure paranoia about ghosts, and it is correct.

> **Check yourself —** Your server has thousands of sockets in `CLOSE_WAIT` and the number keeps climbing. Which side closed first, and whose bug is it?

<details>
<summary>Answer</summary>

The *other* side closed first — `CLOSE_WAIT` means "I received their FIN and have not sent mine." The kernel is waiting for **your application** to call `close()`. A growing `CLOSE_WAIT` count is an application leaking descriptors, not a network fault; contrast `TIME_WAIT`, which accumulates on the side that closed first and is entirely normal.

</details>

### Can you catch a connection in TIME_WAIT?

In `docker run --rm -it --privileged --network host --name lab nicolaka/netshoot`, create a `TIME_WAIT` and catch it in the act. Run the second command *immediately* after the first.

> **Predict first —** `curl` has already finished and printed the page. How many connections will `ss` show now, and in what state?

```bash
curl -s google.com > /dev/null
ss -tan state time-wait
```

The connection is finished — `curl` has exited, the page was fetched and discarded — and yet there it is, a row in `TIME_WAIT`, local port still reserved. This is not a leak; it is correct. Wait a minute and run `ss -tan state time-wait` again and it is gone, expired into `CLOSED`.

For the big picture, `ss -s` prints a summary: total sockets and a breakdown by state, including how many are in `TIME_WAIT`. On a busy client that opens and closes many short connections, that `TIME_WAIT` count can run into the thousands — all correct, all guarding ports.

**So two commands are enough to catch the kernel keeping books on a connection that no longer exists — and the record it keeps is the state, which is the only place the connection ever lived.**

> **You understand this when you can** fetch a URL, immediately find the finished connection in `TIME_WAIT` with `ss`, name the four-tuple that row is refusing to release, and explain why the kernel is holding a record of a connection you already closed.

Everything above is one kernel remembering its *own* conversations — the sockets this machine opened and accepted. But a machine can also sit in the middle of conversations that are not its own, forwarding them on behalf of others, and rewriting their addresses as they pass. What must a machine remember *then*, and where does it write that down? That is the next lesson.

---

← Prev: **[The three-way handshake](01-tcp-handshake.md)** · ↑ **[Act III overview](README.md)** · Next: **[conntrack — the kernel's flow table](02b-conntrack.md)** →
