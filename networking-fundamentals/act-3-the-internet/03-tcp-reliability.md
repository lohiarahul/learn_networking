# TCP and reliability

IP gets a packet from one machine to another, or it doesn't — and it never apologizes. A router under load drops your packet. Two packets take different paths and arrive out of order. A retransmission you didn't ask for shows up twice. IP promises nothing except that *if* a packet arrives, it arrived at the right address. Two processes that want to have an actual conversation — send a file, run a request, stream a reply — cannot live with that. So somewhere a layer has to take this hostile, lossy channel and turn it into something a program can trust. That layer is TCP, and the trust it sells is a lie maintained with enormous care.

### Why should the kernel, not every app, handle reliability?

**Because the code is subtle, identical in every program that needs it, and corrupts data silently when it is wrong.**

In the mid-1970s, with the network declared unreliable by design (the bet Cerf and Kahn made in 1974), someone still had to make a file arrive intact. The application programmer should not have to write retransmission logic, reordering buffers, and congestion control into every program that touches the network.

The pain was concrete: without a common reliability layer, every application reinvents the same hard machinery, and most get it wrong. TCP was the answer — write the hard part once, in the kernel, and hand programs a simple promise.

### So what does TCP guarantee, and what does each guarantee cost?

**Three guarantees — delivery, order, integrity — paid for with memory, buffering, and computation respectively.**

TCP makes an unreliable packet network look like a reliable, ordered stream of bytes. Two *processes* open a connection and from then on one calls `write()` and the other calls `read()` as if they were piping bytes to each other in the same room. Processes, not machines — that distinction is load-bearing rather than pedantic, and you have already proved it: one machine held thousands of sockets at once in `/proc/net/tcp`, each one a different conversation belonging to a different process. A connection is between two endpoints in that table, never between two boxes. The network's cruelty is hidden entirely inside the kernel.

| Guarantee | How TCP keeps it | What it costs |
| --- | --- | --- |
| **Delivery** | The kernel keeps a copy and retransmits until the far side acknowledges it | Memory (the copy) and latency (waiting to find out it was lost) |
| **Order** | Every byte carries a sequence number; the receiver reassembles by number | Buffering — a byte that arrives early must wait for its predecessors |
| **Integrity** | Every segment carries a checksum; a failed checksum means discard and retransmit | The checksum computation, on every segment |

You get a clean stream; the kernel pays the bill.

### Why send a whole window instead of one segment at a time?

**Because one-at-a-time caps you at a single segment per round trip, however fast the link is.**

The naive way to guarantee delivery is to send one segment, wait for its acknowledgment, then send the next. Over a link with any real round-trip time this is agonizing — you spend almost all your time waiting. TCP instead keeps a *window* of bytes in flight: it sends many unacknowledged segments at once (pipelining) and slides the window forward as acknowledgments arrive.

<!-- figure -->

```
  the sender's byte stream, by sequence number:

  ... 1000 1001 ............ 4000 4001 ......... 6000 6001 ...
      └── acknowledged ──┘ └─ sent, not yet ──┘ └─ allowed but ─┘
          (kernel may          acknowledged        not yet sent
           free these)         (in flight)        (window has room)
                              └──────── send window ────────┘
                                        size = N bytes

      ◄── window slides right as ACKs arrive ──►

  ACK for 4000 arrives  ──►  left edge jumps to 4001,
                             those copies can be freed,
                             right edge advances, new bytes may go out
```

Without the window — without multiple segments in flight at once — TCP would be painfully slow, capped at one segment per round-trip. The window is why TCP can fill a fast link.

So how big is it, and who decides?

### Where can you see the bytes in flight?

**In the `tx_queue` column of `/proc/net/tcp` — a hex byte count of data the kernel is still holding, unacknowledged.**

A live connection's in-flight bytes are visible in the kernel's own table:

```
/proc/net/tcp     one row per IPv4 connection; columns include tx_queue:rx_queue
```

The `tx_queue` field is the number of bytes the kernel has queued to send but not yet had acknowledged — your in-flight window, made of real bytes sitting in kernel memory. The `rx_queue` field is bytes received and buffered but not yet read by the application. A raw row looks like this (one line, fields space-separated):

<!-- annotate: proc-net-tcp-row -->

```
  sl  local_address rem_address   st tx_queue:rx_queue ...
  0: 0100007F:1F90 0100007F:C1A2 01 00000140:00000000 ...
                                  │  └tx──┘ └rx──┘
                                  │  0x140 = 320 bytes   0 bytes
                                  └ st=01 = ESTABLISHED
```

So `tx_queue` of `00000140` is hex for 320 bytes the kernel is still holding, unacknowledged, ready to retransmit.

The tool `ss` reads exactly this and prints it humanely: it labels the state by name and shows the two queues as decimal `Recv-Q` and `Send-Q`. It invents nothing; it decodes that hex. Two new flags from here on: `-m` adds the socket's memory accounting (a `skmem:(...)` line — glance at it and move on, it is a breakdown of the same buffers), and `-i` adds the kernel's per-socket internals. We will need `-i` shortly and not before, so leave it alone until then.

> **Check yourself —** Your application logs that it finished writing the whole response. Has the client received it?

<details>
<summary>Answer</summary>

No — `write()` returning only means the bytes were copied into the kernel's send buffer. They sit in `tx_queue`, unacknowledged, until the far side confirms them. `ss -tmi` showing a large `Send-Q` is the difference between "my app is slow" and "the network or the client is slow," and it is the single most common confusion at this layer.

</details>

### Can you watch flow control freeze a sender?

In `docker run --rm -it --privileged --network host --name lab nicolaka/netshoot`, make a connection that deliberately sends faster than the reader drains, and watch bytes pile up in the queues. In one terminal, start a slow reader:

```bash
nc -l 8080 | (sleep 30; cat)
```

That listens on 8080 but does not read for 30 seconds. In a second terminal (`docker exec -it lab zsh`), fire a flood at it:

```bash
yes "filling the window" | nc 127.0.0.1 8080
```

Now in a third terminal, watch the queues — first through `ss`, then in the raw file. (`dst :8080` is `ss`'s address filter, the sibling of the `state …` filter you already use: it keeps only sockets whose *destination* port is 8080, which here means the sender's side of this connection.)

> **Predict first —** as you flood a reader that isn't reading, will the sender's `Send-Q` climb forever, or stop? Why?

```bash
ss -tmi dst :8080
grep ':1F90' /proc/net/tcp     # 1F90 = 8080; the tx_queue:rx_queue hex columns are the bytes in flight
```

The surprising result: the `Send-Q` on the sender climbs and then *stops* — it does not climb forever. Why? Because the receiver's buffer filled up, the receive window it advertised dropped toward zero, and TCP flow control froze the sender. The sender is not allowed to outrun what the receiver can hold.

You can watch the ceiling itself rather than only its effect. Leave the flood running and sniff the connection with a tool you earned in Act II:

```bash
tcpdump -i any -nn tcp port 8080
```

Every acknowledgement the reader sends carries a `win` field, and that number *is* the receive window — the receiver saying, in every single ACK, "this much more and no further." Watch it shrink as the buffer fills. The sender is not guessing at this limit; it is being told, continuously, in a field of every reply.

The window you drew is doing its job right now, throttling a `yes` loop to the speed of a `sleep`. When the reader wakes after 30 seconds, the queues drain and `win` opens up again.

**So one limit on the window is the receiver's advertised ceiling, it arrives in the `win` field of every ACK, and you can watch a sender walk straight into it and stop.**

### The receiver has room. Why would the sender still hold back?

Flow control protects the *receiver*. Nothing in it protects anything in between.

Picture the receiver as a machine with gigabytes of buffer, cheerfully advertising an enormous window, reachable only across a link that can carry a tenth of what you want to send. Flow control says "go ahead." Every router on the path has a finite queue; when packets arrive faster than a queue drains, the queue grows, and when it is full the router drops whatever comes next and feels no remorse. Send at the receiver's pace and you will bury the narrowest link on the path, lose packets, retransmit, and lose those too.

Now notice the shape of the problem. The receiver can *tell* you its limit — it is one number in a header. The network cannot tell you anything. There is no field in which a router announces "I am nearly full," no protocol by which the path reports its own capacity. The sender must discover a number nobody will ever send it, on a path that changes minute to minute, shared with strangers whose traffic it cannot see.

So it guesses, and corrects. TCP keeps a second window of its own invention — the **congestion window**, `cwnd` — and the bytes it is actually allowed to have in flight are the *smaller* of the two:

```
   bytes allowed in flight  =  min( receive window , congestion window )
                                   └─ receiver's ─┘  └─ sender's guess ─┘
                                      ceiling            about the path
```

The receive window is told to you. The congestion window is a hypothesis the sender maintains about a path it cannot see, and every acknowledgement is evidence for it.

### Can you watch the sender's guess grow?

In the lab container, put a bulk transfer on loopback — this time with a reader that reads as fast as it can, so nothing is flow-controlled and only `cwnd` is in charge. In one terminal:

```bash
nc -l 8080 > /dev/null
```

In a second terminal, flood it:

```bash
yes "bulk payload line" | nc 127.0.0.1 8080
```

The sender's guess is not a private thought. It is a number the kernel keeps, in the same row of the same file you have been reading all act — and Act I already showed it to you and told you to come back for it. Fields 1 to 10 of a `/proc/net/tcp` row are the named interface; fields 11 to 17 are TCP's unnamed internal tuning state, and Act I's field table said of them: *the congestion window is in there, and these are Act III's subject*. Cash that in. Field 16 is `cwnd`; on an established row, field 17 is the slow-start threshold.

> **Predict first —** loopback never drops a packet and has no router in the middle. Sample the sender's numbers three times, a second apart: does the congestion window sit at one value, climb, or bounce up and down?

```bash
awk '$3 ~ /:1F90$/ {print "cwnd=" $16, "ssthresh=" $17}' /proc/net/tcp
sleep 1; awk '$3 ~ /:1F90$/ {print "cwnd=" $16, "ssthresh=" $17}' /proc/net/tcp
sleep 1; awk '$3 ~ /:1F90$/ {print "cwnd=" $16, "ssthresh=" $17}' /proc/net/tcp
```

(Column 3 is `rem_address`, so `$3` ending `:1F90` picks the *sender* — the socket whose remote port is 8080 — and skips the listener and the receiver's own row, which carry 8080 in column 2 instead.)

Two findings. First, `cwnd` is *large* — hundreds, often thousands, orders of magnitude past where a connection begins. If it is still moving between your samples you are watching it climb; if it has parked at some enormous value it climbed there in the first fraction of a second and then stopped bothering, because nothing on this path has ever pushed back. Loopback is a path with no congestion, and the sender's guess about it reflects that exactly — which tells you what this number is measuring, because it is plainly not measuring the receiver.

Second, `ssthresh` reads `-1`. That is the kernel's way of writing "unset": the threshold is the value `cwnd` gets cut *back* to after trouble, and this connection has never had any trouble in its life, so there is nothing to remember. A `-1` here is a connection that has never lost a packet.

Now for the tool. Act I warned you these fields are unnamed, undocumented, and reshuffled between kernel versions — which is exactly the argument for a program that knows the layout for your kernel and labels it:

```bash
ss -ti dst :8080
```

`-i` is the flag we deferred earlier. It prints the same internals with names on: `cwnd:` and `ssthresh:` (omitted entirely when unset, rather than shown as `-1`), plus `rtt:` — the smoothed round-trip estimate and its variance in milliseconds — and `bytes_acked:`, the running total the far side has confirmed. Much of the rest of that line is none of your business yet; ignore it. You will also see a word like `cubic:` at the front, which is the *name* of the algorithm doing the guessing. Note that several exist and that yours has a name; which one and why is a question for another day.

Now watch a connection that *does* cross a network. Open one to a real host with `nc` and just leave it sitting there — type nothing, send nothing:

```bash
nc example.com 80
```

In another shell, read its numbers:

```bash
ss -ti dst :80
```

Here `rtt:` is a real measurement — some genuine number of milliseconds, the ruler this connection is using — and `cwnd` is small: typically `cwnd:10`. Ten segments is Linux's **initial window**, and it is all TCP is willing to put on an unknown path before it has any evidence at all. In bytes that is ten times the largest segment this path allows — with Act II's 1500-byte MTU, about 1460 bytes of payload each, so roughly 14 KB. This connection has sent nothing, so it has earned nothing, so it is still holding the guess it was born with. Press Ctrl-C on the `nc` when you're done.

Two connections, two guesses about two paths, both read out of the same two fields. The receiver never came into it.

### How does the guess get corrected?

**By treating a lost packet as the network's only available way of saying "too much" — so `cwnd` ramps up while nothing is lost and is cut hard the moment something is.**

Start from that initial window of ten segments. Everything gets acknowledged, so the path can clearly take more. TCP raises `cwnd` — roughly *doubling* it every round trip, since each acknowledged segment permits two more. That is **slow start**, and its name is a joke about where it begins, not how it proceeds: doubling per RTT is exponential, and a connection reaches a fast link's capacity in a handful of round trips.

It cannot double forever, and the way it finds out is by going too far. A queue somewhere fills, a router drops a segment, and an acknowledgement that should have arrived does not. That absence is the only signal the network ever sends, and TCP reads it as *the pipe is full*. It records the size at which trouble began in `ssthresh` — the slow-start threshold, roughly half the window that broke — cuts `cwnd` back toward it, and from then on grows *linearly*: one segment more per round trip, probing gently rather than doubling.

That is the whole shape of it, and it explains the throughput curve you have watched a thousand times without naming:

<!-- figure -->

```
 cwnd
   │
   │          ╱│      ╱│     ╱│     ╱│    congestion avoidance:
   │        ╱  │    ╱  │   ╱  │   ╱  │    +1 segment per RTT,
   │      ╱    ▼  ╱    ▼ ╱    ▼ ╱    ▼    cut back on each loss
   │    ╱
   │  ╱   ← first loss: ssthresh := about half of this, cwnd cut to it
   │ ╱
   │╱     ← slow start: cwnd doubles every RTT until the first loss
   └──────────────────────────────────────────────────► time

   ▼ = one lost packet — the only message the network ever sends.
```

A download that starts slow and then surges is slow start finding the ceiling. A transfer that settles into a sawtooth is congestion avoidance living just under it, deliberately overshooting now and then to check whether the ceiling has moved. A connection that collapses to a crawl and recovers slowly has taken losses and cut back. None of this is the receiver being slow, and none of it is your application: it is a sender revising a hypothesis about a path.

Neither experiment above could show you the sawtooth, and it is worth being honest about why: loopback cannot lose a packet, and the idle connection to `example.com` never sent enough to strain anything. To *see* `cwnd` cut you need a path that drops, which means either a real congested link or a deliberately damaged one — a tool this act does not introduce. So take the ramp as observed and the cut as reasoned, and know which is which.

### Why does your call stutter while the download stays fast?

You have lived this one. A big file is downloading; the speed test says the line is fine; the download does not slow down at all — and your video call breaks up, and your typing lags in a terminal. Nothing is *broken*, and nothing has been lost. So where is the delay coming from?

Go back to the router's queue. It does not drop the instant it is oversubscribed. First it *fills* — that is what it is for, absorbing a burst rather than discarding it. But a full queue is a waiting room, and every packet behind your download waits its turn in it. Your call's packets are small, urgent, and stuck at the back of a line of bulk data. So the first symptom of pushing a link too hard is not loss at all: it is latency, arriving long before any packet is dropped, and invisible to any test that measures only throughput. The queue is doing exactly its job, at a size that happens to store whole seconds of traffic.

That is **bufferbloat**, and it is why "my connection is fast" and "my connection feels awful" are both true at once. You can measure it on your own line at the bottom of this page.

> **You understand this when you can** point at one `ss -ti` line plus one `tcpdump` ACK and name each limit separately — the receiver's ceiling from the `win` field (and its consequence in `Send-Q`, or the `tx_queue` hex converted to decimal), and the sender's own guess from `cwnd`, in segments — then say which of the two you would expect to change when the reader stops reading, which when a router starts dropping, and why a large `Send-Q` on its own does not tell you which of the two is to blame.

### What will this ask of you in a cluster?

You now have two questions to carry, both of them about who owns which limit.

**First:** the sender's guess about a path is built up over many round trips, and it is thrown away when the connection closes. So what is the cost of a system whose components open a fresh connection for every request — and what would it be worth to keep one connection alive instead? **Second:** `write()` returning is not delivery; the bytes sit in a `Send-Q` on the sending machine. In a cluster, whose machine is that, and if you can only get a shell somewhere *near* the sender, how would you read the queue belonging to the process that actually wrote the bytes?

Both come due in Act IV and Act V. You already know which files hold the answers.

> **On your own machine —** put a ruler on the network and then watch congestion control's real bill: measure how far away a server actually is in milliseconds, then watch your call stutter during a download — not because packets are lost, but because a router's queue is holding them — in [Act III in the wild](in-the-wild.md#distance-measured-in-milliseconds-speed-of-light).

---

← Prev: **[conntrack — the kernel's flow table](02b-conntrack.md)** · ↑ **[Act III overview](README.md)** · Next: **[HTTP](04-http.md)** →
