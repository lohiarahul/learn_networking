# Act I — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act I. This checks whether you can *use* it. Real
failures never arrive labelled "this is a bind bug" — they arrive as a symptom, a shrug, and a ticket.
Each drill below puts your machine into a **real broken state** (not a story), hands you only the
symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or
   tool would prove it — *then* look.
3. **Open the reveal only after you've tried.** It's collapsed for a reason.

**Where:** inside the `lab` container (`docker run --rm -it --privileged --name lab netlab`). One shell
is enough — each broken server runs in the background. Drill 3 needs the `--privileged` flag (it uses a
raw-socket scan), which the lab already has.

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

## Drill 1 — "It works for me, but they can't reach it"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"The service is up — I can `curl` it on the box all day. But every other container gets
> `connection refused`. The process is running, the port's right. What gives?"*

**Reproduce it** (run; don't read):

```
python3 -m http.server 8080 --bind 127.0.0.1 >/tmp/svc.log 2>&1 &
```

**Confirm the symptom:**

```
curl -s -o /dev/null -w 'from this box -> %{http_code}\n' 127.0.0.1:8080
curl -s -o /dev/null -w 'from outside  -> %{http_code}\n' --max-time 2 "$(hostname -i):8080" \
  || echo 'from outside  -> connection refused'
```

You'll see `from this box -> 200` and `from outside -> connection refused`. The server answers on one
address and refuses on the other.

**Your move.** Same process, same port — so why does the *address you knock on* change the answer?
Which single command shows you what the server actually bound to?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

One command tells the whole story:

```
ss -tlnp | grep 8080
```

```
LISTEN 0  5  127.0.0.1:8080  0.0.0.0:*  users:(("python3",pid=7,fd=3))
```

The `Local Address` is **`127.0.0.1`**, not `0.0.0.0`. The server bound the *inside door only* — so a
knock on the container's real address (`eth0`) finds nobody listening. Read it straight from the kernel
if you like: `grep 1F90 /proc/net/tcp` shows `local_address` `0100007F:1F90` → `127.0.0.1:8080`
(the little-endian flip from lesson 5), where a healthy bind would be `00000000:1F90` → `0.0.0.0:8080`.

**Root cause:** bound to loopback instead of all interfaces (lessons 4 and 5). **Fix:** bind `0.0.0.0`
(`--bind 0.0.0.0`, or minihttp's `INADDR_ANY`). **Why it's worth a whole drill:** this is the single
most common Kubernetes Pod-networking bug — it passes every `kubectl exec … curl localhost` test and
refuses every Service connection, because `kube-proxy` knocks on the *outside* door.

**Cleanup:** `kill %1`

</details>

---

## Drill 2 — "It leaks, and a restart fixes it for a while"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"This service's open-handle count climbs all day. Eventually it starts refusing
> connections; we restart it and it's fine again for a few hours. CPU and memory look normal the whole
> time. We've restarted it on a cron as a 'fix'."*

**Reproduce it** (run; don't read):

```
cat > /tmp/svc.py <<'PY'
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 8080)); s.listen(16)
keep = []
while True:
    conn, _ = s.accept()
    keep.append(conn)          # serve the caller... and never let go
PY
python3 /tmp/svc.py >/tmp/svc.log 2>&1 &
```

**Send it some traffic** — ten callers connect and hang up:

```
python3 -c 'import socket
for _ in range(10): socket.create_connection(("127.0.0.1",8080)).close()'
```

**Your move.** The server "handled" all ten — no errors. But the ticket says it's *holding onto*
something. From lesson 1: which file shows you everything a process is holding? Find the leak, then
explain what's leaking and why.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

**Lens 1 — count what the process holds** (lesson 1's fd table):

```
pid=$(pgrep -nf svc.py)
ls /proc/$pid/fd | wc -l
```

It sits well above the 4–5 a healthy server keeps — one extra descriptor for *every* caller. Send ten
more connections and run it again: the count climbs by exactly ten. That's a leak, live.

**Lens 2 — what state are those sockets in** (lesson 5b):

```
ss -tan state close-wait | grep :8080
```

```
CLOSE-WAIT 1 0 127.0.0.1:8080 127.0.0.1:35284
CLOSE-WAIT 1 0 127.0.0.1:8080 127.0.0.1:35330
...
```

A pile of **`CLOSE-WAIT`** on the server side. `CLOSE_WAIT` means *the other end hung up (sent its FIN)
but our application never called `close()`*. (With real `lsof` from `netlab`: `lsof -p $pid` lists the
same held sockets.)

**Root cause:** the server `accept()`s each connection and **never `close()`s it** — it's exactly the
`close(conn_fd)` line from minihttp's loop (lesson 3), deleted. Every caller permanently costs one row
in the fd table (lesson 1). The graphs lie because the resource leaking is *descriptors*, not CPU or
memory.

**Where it ends if you don't catch it** (lesson 3's ceiling):

```
kill %1
( ulimit -n 64; python3 /tmp/svc.py >/tmp/svc.log 2>&1 ) &
python3 -c 'import socket
for _ in range(120):
    try: socket.create_connection(("127.0.0.1",8080))
    except OSError: pass'
sleep 1; tail -2 /tmp/svc.log; ss -tlnp | grep 8080 || echo "listener is GONE"
```

The log ends in `OSError: [Errno 24] Too many open files` and the listener has vanished — the leak hit
the descriptor ceiling (`EMFILE`) and took the server down. *That's* the "starts refusing connections,"
and the restart "fixes" it only by resetting the count.

**Fix:** `close()` every descriptor you `accept()`. **Cleanup:** `pkill -f svc.py`

</details>

---

## Drill 3 — "We were scanned, but the logs are clean"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Security flagged a port scan against this host overnight. Our application logged zero
> connections all night. So nothing actually happened — right?"*

**Reproduce it** (run; don't read) — a listener with every `accept()` traced:

```
strace -f -e trace=accept,accept4 python3 -m http.server 8080 >/dev/null 2>/tmp/accepts.log &
```

**Your move.** Can someone find your open port *without your application ever seeing a connection*?
Test it: scan the port two different ways, and after each, check whether the app's `accept()` actually
fired.

```
nmap -sS -p 8080 127.0.0.1 | grep 8080/tcp     # SYN ("stealth") scan
grep -c -e accept -e accept4 /tmp/accepts.log    # did accept() fire?
nmap -sT -p 8080 127.0.0.1 | grep 8080/tcp     # connect scan
grep -c -e accept -e accept4 /tmp/accepts.log    # and now?
```

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```
8080/tcp open  http-proxy        ← SYN scan: port found OPEN
0                                 ← accept() fired 0 times — the app saw NOTHING
8080/tcp open  http-proxy        ← connect scan: port found OPEN
1                                 ← accept() fired once — now the app saw it
```

Both scans found the port. Only the **connect** scan (`-sT`) reached the application; the **SYN** scan
(`-sS`) mapped your open port while `accept()` never fired and your logs stayed empty.

**Root cause:** the application is woken only at `ESTABLISHED` — the hinge from lesson 5b. A SYN scan
sends the SYN, reads the SYN-ACK (which already proves the port is open), then sends `RST` instead of
the final ACK, so the handshake never completes and `accept()` never returns. **Clean application logs
are not proof you weren't scanned.** To see it, you have to drop to where the SYN *was* visible — the
kernel (firewall logs, `conntrack`, and eBPF tools like Falco/Cilium, which is exactly why cluster
security watches the kernel, not app logs).

*(`-sS` needs the privileged lab for raw sockets — same as lesson 5b.)*

**Cleanup:** `kill %1` (and `pkill -f http.server` if it lingers)

</details>

---

## Where this leaves you

You just did the thing the whole act was building toward: meet a failure as a bare symptom, form a
hypothesis, and open the right kernel file to confirm it — with nobody telling you which idea applied.
A bind that answers one door and not the other; a descriptor leak hiding behind flat CPU graphs; a scan
your application is structurally blind to. That gap — between *knowing* the mechanism and *reaching for
it under fire* — is the one this drill closes.

When two machines have to talk, every failure mode here returns with a wire added and new ones appear.
That's Act II.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act I overview](README.md)** · Next: **[Act II — Two machines](../act-2-two-machines/README.md)** →
