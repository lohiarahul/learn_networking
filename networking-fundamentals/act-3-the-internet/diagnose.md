# Act III — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act III. This checks whether you can *use* it. Real
failures never arrive labelled "that's a SYN with no reply" or "the send queue is full" — they arrive as
a symptom, a shrug, and a ticket. Each drill below puts your machine into a **real broken state** (not a
story), hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or
   tool would prove it — *then* look.
3. **Open the reveal only after you've tried.** It's collapsed for a reason.

**Where:** inside the lab container with the host's real network attached —
`docker run --rm -it --privileged --network host --name lab nicolaka/netshoot`.

**Read this part before you start.** `--network host` means what it says: the container does not get its
own network namespace, it *shares the host's*. There is no separate copy of the network to throw away, so
these drills are not sandboxed. Drill 1 installs a real route on the real machine; drill 4 lowers a real
kernel limit on the real machine's flow table. Both survive `exit`, because `exit` only ends a process —
it does not undo a routing table entry or a `sysctl`. So:

- **Every drill's `Cleanup` line is mandatory**, not tidiness. Run it before moving on.
- **Drill 4 records the value it is about to change** and its `Cleanup` restores *that recorded value*.
  Your host's default is yours; nobody can guess it for you. Don't skip either half.
- On **macOS or Windows**, "the host" is the small Linux VM Docker runs in, so the blast radius is that
  VM and restarting Docker clears anything you miss. On a **Linux** machine the host is the machine you
  are sitting at, and a throttled flow table there will throttle everything you do — run these in a
  throwaway VM if you can.

A couple of drills want a second and third shell — `docker exec -it lab zsh` into the same container, or
use `tmux`. The `--privileged` flag is what lets you read `conntrack`, edit routes, and change kernel
limits — which is also precisely why the changes reach the host.

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Five rather than seven, because each of these drills has a narrower surface than an exam task — one machine, or two, and a handful of files.

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

## Drill 1 — "The new API just hangs — no error, nothing"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Connecting to the new payments API times out after a few seconds. Not `connection
> refused` — it just sits there, then gives up. Every other host is instant. DNS resolves fine, the IP
> looks right. It's like our packets fall into a hole."*

**Reproduce it** (run; don't read):

```bash
ip route add blackhole 93.184.216.0/24
```

**Confirm the symptom:**

```bash
curl -s -o /dev/null -w 'good host -> %{http_code}\n' --max-time 3 https://1.1.1.1 \
  || echo 'good host -> failed'
curl -s -o /dev/null -w 'the API  -> %{http_code}\n' --max-time 3 https://93.184.216.34 \
  || echo 'the API  -> timed out'
```

One host answers instantly; the API sits for the full timeout and then gives up. No `refused`, no reset
— just silence.

**Your move.** From the handshake chapter: `connection refused` is a *reply* (a RST — the host is there
and saying no). Silence is different. Start a connection to the API and, before it times out, look at
what state the kernel parks it in — and whether the SYN is getting *any* answer at all.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

**Lens 1 — what state is the stuck connection in?** In one shell, start a slow-dying connect; in a
second, read the table:

```bash
curl -s --max-time 10 https://93.184.216.34 &     # leave it hanging
ss -tan state syn-sent 'dst 93.184.216.0/24'
```

```
State      Recv-Q Send-Q  Local Address:Port   Peer Address:Port
SYN-SENT   0      1       10.0.2.15:41678      93.184.216.34:443
```

It's stuck in **SYN-SENT** (`st` = `02` in `/proc/net/tcp` — `grep ' 02 ' /proc/net/tcp` shows the same
row). SYN-SENT means "I sent my SYN and I'm still waiting for the SYN-ACK." It never comes.

**Lens 2 — is the SYN even being answered?**

```bash
tcpdump -i any -nn "host 93.184.216.34 and tcp port 443"
# (re-run the curl in another shell)
```

You'll see the same `[S]` (SYN) leave every few seconds — 1s, 2s, 4s… doubling — and **nothing come
back**. That is the handshake chapter's third outcome exactly: not a SYN-ACK (works), not a `[R]` RST
(actively refused), but *silence* — the SYN is being dropped and TCP is retransmitting with exponential
backoff until it gives up.

**Root cause:** packets to that range are being silently discarded before they reach anything that could
answer — here a local `blackhole` route eating them; in the wild, silence means "the packet is being
dropped somewhere — a firewall rule, a missing route, a full connection-tracking table" (the handshake
lesson), and never a connection refused. The RST-versus-silence fork told you which half of the world to
look in. **Fix:** find and remove whatever is dropping the SYN.

**Cleanup (mandatory — this route is on the host):** `ip route del blackhole 93.184.216.0/24`

</details>

---

## Drill 2 — "The app logged 'upload complete' but the client is still waiting"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Our service logs `finished writing response` and moves on, but the client swears it's
> still downloading thirty seconds later. The app is done — so why isn't the client? Is the network
> eating our data?"*

**Reproduce it** (run; don't read) — a reader that accepts the connection but stops reading, and a
writer that floods it:

```bash
nc -l 8080 | (sleep 30; cat) &          # a "slow client": accepts, then reads nothing for 30s
sleep 1
yes "payload line that fills the pipe" | nc 127.0.0.1 8080 &    # the "app" writing hard
```

**Confirm the symptom:** the writer's `nc` (the "app") has handed all its bytes to the kernel and would
happily report "done" — yet nothing is arriving at the reader, and won't for 30 seconds.

**Your move.** The application called `write()` and returned. But `write()` returning only means the
bytes reached the *kernel's send buffer* (the reliability lesson), not the far side. Which field of the
connection's row tells you how many bytes are sitting unsent-and-unacknowledged right now — and why
would it be stuck?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
ss -tmi dst :8080
```

```
ESTAB  0  2626560  127.0.0.1:53812  127.0.0.1:8080
       skmem:(...) ... cwnd:10 ...
```

The **Send-Q** is large and *not draining* — hundreds of KB the sender handed the kernel that cannot go
anywhere. Read it raw if you like: `grep ':1F90' /proc/net/tcp` and decode the `tx_queue` hex (the
reliability lesson) — it's a non-zero byte count, the in-flight/queued bytes made of real kernel memory.

**Why it's frozen:** the receiver isn't calling `read()`, so its receive buffer filled, so it advertised
a **zero receive window**, so TCP flow control froze the sender mid-stream. The window is
doing its job — throttling the writer to the speed of the reader. When the reader wakes after 30s and
drains, the Send-Q collapses to 0 and the transfer completes.

**Root cause:** not a network fault and not data loss — a slow (or stuck) *consumer*. `write()` returning
is not delivery. **This is the single most common "the app said it finished but the client is waiting"
confusion**, and `ss -tmi` settles it in one line: bytes stuck in Send-Q → the far side isn't reading;
Send-Q empty → the app hasn't actually sent, or it *was* delivered.

**Cleanup:** `pkill -f 'nc -l 8080'; pkill -f 'nc 127.0.0.1 8080'`

</details>

---

## Drill 3 — "curl works with a flag, the browser screams, and DNS is fine"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Half the team says the internal service is up — `curl` gets a 200. The other half gets a
> big red 'your connection is not private' in the browser and refuses to load it. The address is right,
> DNS is right, it's clearly serving. Who's wrong?"*

**Reproduce it** (run; don't read) — stand up a TLS server whose certificate nobody vouches for:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -keyout /tmp/k.pem -out /tmp/c.pem -subj '/CN=localhost' >/dev/null 2>&1
openssl s_server -quiet -accept 8443 -cert /tmp/c.pem -key /tmp/k.pem \
  -www >/tmp/tls.log 2>&1 &
```

**Confirm the symptom:**

```bash
curl -s  -o /dev/null -w 'plain curl -> %{http_code}\n' https://localhost:8443 \
  || echo 'plain curl -> REJECTED the certificate'
curl -sk -o /dev/null -w 'curl -k   -> %{http_code}\n' https://localhost:8443
```

Plain `curl` refuses (`SSL certificate problem`); `curl -k` (which skips verification) gets a `200`. The
server is genuinely serving TLS — so it isn't down, and it isn't DNS.

**Your move.** The bytes flow, the handshake completes, the port is right. The disagreement is about
*trust*, not reachability. Which tool opens the TLS layer by hand and tells you, in plain text, whether
the certificate chain reaches a root your machine trusts — and what its verdict is here?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
echo | openssl s_client -connect localhost:8443 2>/dev/null | grep -E 'Verify return code|subject=|issuer='
```

```
subject=CN = localhost
issuer=CN = localhost          <- it signed itself
Verify return code: 18 (self-signed certificate)
```

The **issuer equals the subject** — the certificate signed itself — so the chain never reaches a CA in
your trust store, and `Verify return code` is non-zero (`18` self-signed, or `21`/`10` for
unable-to-verify / expired). That is exactly the `Verify return code: 0` from the TLS chapter *failing*:
`0` means "a CA I trust vouched for this binding"; anything else means the lock refused to close.

**Root cause:** the server presents a certificate no trusted CA signed (self-signed here; in the wild, an
expired cert, a missing intermediate, or the wrong hostname). `curl -k` and "click through the warning"
*bypass* verification — which is why one half of the team "succeeded": they turned the check off. The
browser is right to scream. **Fix:** issue a cert from a trusted CA (or, inside a cluster, from
`cert-manager`), or add the CA to the client's trust store — never paper over it with `-k` in
production.

**Cleanup:** `pkill -f s_server; rm -f /tmp/k.pem /tmp/c.pem`

</details>

---

## Drill 4 — "Timeouts under load, and they clear when traffic dies down"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Under peak traffic a fraction of connections just time out — no RST, no application error,
> nothing in the logs. When the load drops it clears itself. CPU, memory, and the app are all healthy.
> It's maddeningly intermittent and only ever under load."*

**Reproduce it** (run; don't read) — squeeze the kernel's flow table until it can't record new
connections. The first line records your host's real default so the `Cleanup` can put back *that*
number and not a guess; run both lines together, and note what the first one prints:

```bash
cat /proc/sys/net/netfilter/nf_conntrack_max | tee /tmp/ct_max_before   # YOUR default. keep it.
sysctl -w net.netfilter.nf_conntrack_max=64 >/dev/null    # a table far too small for real load
```

**Confirm the symptom** — throw a burst of connections at it and read the two numbers that matter:

```bash
for i in $(seq 1 40); do (curl -s --max-time 2 https://1.1.1.1 >/dev/null &) ; done
conntrack -C                                       # how many connections tracked right now
cat /proc/sys/net/netfilter/nf_conntrack_max       # the ceiling
dmesg 2>/dev/null | tail -3                         # the kernel may be shouting about it
```

Under the burst, the count crowds right up against the ceiling — and some of those `curl`s time out with
no error of their own.

**Your move.** No RST means nobody refused you (drill 1's fork). No app error means it never reached the
app. Something *below* the app is dropping packets only when busy. Which kernel table has a hard size
limit, records every connection, and — when full — drops new packets *silently*? Read its current
occupancy against its limit.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
conntrack -C                                    # e.g. 64
cat /proc/sys/net/netfilter/nf_conntrack_max    # 64  -> count has hit the ceiling
```

The **count has reached `nf_conntrack_max`**. `conntrack` records every connection so replies
can be matched and un-NATted; the table is finite. When it fills, the kernel *cannot record a new
connection, so it silently drops the packet* — no RST, no error, just the "SYN with no reply" from drill
1, appearing only under enough load to fill the table, and clearing the moment entries expire and free
slots. You can watch entries churn with `conntrack -E` and snapshot with `conntrack -L`; the smoking gun
is `dmesg` printing `nf_conntrack: table full, dropping packet`.

**Root cause:** conntrack table exhaustion — "when those two numbers get close, you have found your
outage" (the conntrack lesson). **This is a marquee Kubernetes failure:** a busy node runs thousands of
short-lived Pod↔Service connections and each eats a slot; a retry-storm or chatty proxy tips it over.
**Fix (operational):** raise `nf_conntrack_max` and/or cut the connection churn — but the *lesson* is
conceptual: a service's reliability is bounded by the size of a kernel table, because a tracked
connection *is* an entry in it.

**Cleanup (mandatory — this limit is the host's, and 64 will throttle everything you do next):**

```bash
sysctl -w net.netfilter.nf_conntrack_max=$(cat /tmp/ct_max_before)
sysctl net.netfilter.nf_conntrack_max      # confirm it matches the number you noted
```

</details>

---

## Where this leaves you

**Before you close the container**, confirm the two host-level changes are gone. `exit` will not do it
for you:

```bash
ip route show | grep blackhole                 # should print nothing
sysctl net.netfilter.nf_conntrack_max          # should match the number you recorded
```

Four failures, one method: meet a bare symptom, decide *which* layer it lives in, and open the one file
or run the one tool that proves it — a SYN dropped into silence versus a RST that refuses; a Send-Q that
won't drain because the far side stopped reading; a certificate that signed itself and a trust store that
won't be fooled; a flow table so full the kernel drops packets without a word. Nobody told you which idea
applied; you ranged across the whole act to find it. RST-versus-silence, `write()`-returned-versus-
delivered, verified-versus-`-k`, and count-versus-limit are the forks you now reach for by reflex.

Every one of these assumed one honest machine per endpoint, each owning its real IP. Act IV breaks that:
one machine pretends to be many, a single address stands in for a crowd, and the conntrack table you just
overflowed becomes the thing that makes it all work.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act III overview](README.md)** · Next: **[Act IV →](../act-4-one-pretends-many/README.md)**
