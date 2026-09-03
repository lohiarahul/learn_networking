# Plan — Phase 5: netfilter as a subject, not a section

*Written 2026-09-02. Coverage numbers below are `grep -rIn` counts over `networking-fundamentals/`,
`drills/`, `reference/` and `exam-prep/`, taken before any of this work began. The harness baseline
this must leave standing is `cd tools && python3 -m harness` clean.*

> **Status: 4 of 4 units shipped and verified.** Every machine-checked invariant passes
> (`cd tools && python3 -m harness` → clean) and every obligation including **item 14** is closed.
>
> Verification took two `technical-accuracy-checker` passes and one `learner-simulator` pass. The first
> accuracy pass found 18 wrong claims (nine load-bearing); the second, run after the corrections, found
> three more that only appear when the lessons are run *in order* rather than block by block — the most
> important being a stale `nat OUTPUT` REDIRECT rule left behind by 03d's own undo block, which kept
> conntrack engaged and silently falsified the whole TPROXY section. Two root causes accounted for six
> of the original failures: `net.bridge.bridge-nf-call-iptables` defaulting to `1` (which hides the
> hairpin bug and breaks `TPROXY`), and locally originated traffic never traversing `nat PREROUTING`.
> Drill 12 was redesigned outright: its premise — `NOTRACK` blinding a working interception — is
> physically impossible, because NAT is implemented on top of the conntrack row. Item 14
> — every command run for real, plus a Spirit/River pass — is outstanding **by explicit choice**, and
> until it runs nothing here may be called shipped. See §4.

## 1. The complaint, and what measuring it found

The reader's complaint was *"iptables isn't covered at length; proxies, firewalls and NATs should all
be covered to burn it in, because most cloud networking relies on it."* Measured, the complaint is
right and mislocated.

[`act-4/03-iptables-and-nat.md`](networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md)
is 3,348 words — above the course median — and its coverage of netfilter's *anatomy* is not thin. It
earns the five hooks from rule counters rather than asserting them, derives the DNAT-in-`PREROUTING` /
SNAT-in-`POSTROUTING` placement from where the routing decision sits, and closes on two genuinely good
shadows (`ufw` watching `INPUT` while container traffic walks `FORWARD`; `iptables-save` blind to a
native nftables table).

What is missing is not depth on the anatomy. It is **everything the anatomy is for.** Each row below
was verified as a zero- or near-zero-hit across the whole course:

| Missing | Hits | Why it is a defect rather than a wish |
|---|---|---|
| `-m conntrack --ctstate ESTABLISHED,RELATED`; a default-deny `INPUT` policy | 0 as a firewall match | [`JOURNEY-MAP.md`](JOURNEY-MAP.md) Stage 8 promises *"security groups are conntrack — stateful, which is why they need no return rule … and now obvious to you."* The reader has never written a stateful firewall rule. **The payoff is promised and unfunded.** |
| `DROP` vs `REJECT` | 0 as a taught distinction | [`the-whole-stack.md`](networking-fundamentals/the-whole-stack.md) and Act V both lean on *"silence, not refusal"* and *"000 after 6s"*. Act I's SYN-scan lesson leans on it harder still: `filtered` vs `closed` **is** this distinction, and nothing defines it. |
| user chains as subroutines; `-j RETURN`; terminal vs non-terminal verdicts | `-j RETURN` 0 | Act V lesson 03 teaches `KUBE-SERVICES → KUBE-SVC → KUBE-SEP` traversal, so the reader *is* taught chain-as-list — but in Act V, on Kubernetes' example, rather than earned on the floor that Act V stands on. |
| SNAT source-port exhaustion; `--random-fully` | 0 | Act III teaches conntrack's *table* ceiling and never NAT's *port* ceiling. This is the arithmetic under every NAT-Gateway port-allocation page. |
| hairpin NAT / NAT loopback | 0 | The mechanism under "a Pod cannot reach its own Service", and under kubelet's `hairpinMode`. |
| `mangle`, packet `MARK`, `-t raw` / `NOTRACK` | `MARK` 2 in passing, `NOTRACK` 0 | `MARK` + `ip rule` is the join between netfilter and the routing table Act II already taught — how VPNs, multi-homed hosts and egress gateways steer. `raw` is the only place the conntrack ceiling can be *opted out of*. |
| `REDIRECT` / `TPROXY`; `SO_ORIGINAL_DST` | 0 | This is literally how a sidecar mesh intercepts traffic. Act X lesson 09 uses the result. |
| forward vs reverse proxy; `CONNECT`; `X-Forwarded-For`; PROXY protocol | XFF 1 hit | The 790 words in Act III lesson 04 teach the L4/L7 split and stop. The one XFF paragraph is in `the-whole-stack.md` — the capstone, i.e. *after* every lesson that depends on it, including `externalTrafficPolicy`. |

**The through-line that makes this one subject rather than seven additions:** every item above is
conntrack cashing a cheque Act III wrote. A stateful firewall is a rule that *asks the flow table a
question*. NAT's ceiling is the flow table's key space running out of free fields. A transparent
proxy recovers the destination it destroyed *by reading its own conntrack row through a socket
option*. The reader meets the table three more times, each time in a role they could not have
predicted from the last.

## 2. Placement, which River decides rather than taste

- **Forward/reverse proxy, `CONNECT`, identity erasure** need HTTP and TCP and nothing else → they
  belong in Act III lesson 04, beside the L4/L7 split that already sits there.
- **A stateful firewall** needs `conntrack` (Act III 02b) and the five hooks (Act IV 03) → earliest
  legal home is Act IV, after lesson 03.
- **`TPROXY`** needs `MARK` *and* `ip rule` → it must follow the `mangle` material, which fixes the
  internal order: firewall → NAT limits → transparent proxy.
- **Everything netfilter stops at lesson 04**, because `04-overlay-vxlan.md` leaves the host and the
  reader should not carry an open netfilter question across that boundary.

Act IV is also the right host on independent grounds: [`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md)
§2.3 measured it as the thinnest floor in the course, holding up everything from Act V on.

Numbering therefore inserts three lessons between the existing 03 and 04, and extends one Act III
lesson in place. **Extending 04-http rather than adding `04b`** is deliberate: a new Act III file would
need Route B step 2's explicit glob list and the exam-path step table amended for material neither
curriculum examines, to separate two halves of one idea the reader meets in one sitting.

## 3. The units

| # | Unit | Words (target) | Status |
|---|---|---|---|
| 5.1 | Act III `04-http.md` — the proxy section extended: forward vs reverse, `CONNECT`, and who the backend thinks the client is | +1,145 (lesson now 5,130) | ✍️ drafted, unverified |
| 5.2 | Act IV `03b-the-stateful-firewall.md` | 3,824 | ✍️ drafted, unverified |
| 5.3 | Act IV `03c-when-nat-runs-out.md` | 3,232 | ✍️ drafted, unverified |
| 5.4 | Act IV `03d-the-transparent-proxy.md` | 2,635 | ✍️ drafted, unverified |

**No new tools.** Every experiment below runs on `iptables`, `conntrack`, `ip rule`, `curl`, `nc`,
`python3` and `sysctl` — all already taught, all already on the roster. That is a design constraint,
not a coincidence: it deletes obligations 6–10 (roster row, `capabilities.json` entry, tool page
regeneration, `SHELL_COMMANDS`, per-act command rows) for four units, and it is honest, because
nothing here needs a tool the reader lacks. `nft` stays where lesson 03 left it.

### 5.1 — Act III lesson 04, proxy section extended

The existing 790 words answer *"how deep does it read?"* (L4 vs L7) and never ask *"who asked for
it?"*. Three beats, in the lesson's existing voice:

1. **Forward vs reverse is not two programs, it is two answers to "who chose me?"** A forward proxy
   is chosen by the client and knows every destination; a reverse proxy is chosen by the *destination*
   and the client believes it *is* the server. Same relay, opposite trust.
2. **`CONNECT`** — the wall: a forward proxy that terminates HTTP cannot terminate HTTPS without
   holding a certificate for a name it does not own. So the client asks it to stop reading:
   `CONNECT host:443` turns an L7 proxy into an L4 tunnel *for one connection*, by request. This is
   the first thing in the course that treats Act III's sealed lock as a constraint on infrastructure
   rather than a promise to the user.
3. **The erasure, posed and not resolved.** A reverse proxy *is* a new client, so the backend's
   `/proc/net/tcp` row names the proxy. `X-Forwarded-For` is a header the proxy chooses to write and
   the backend chooses to believe — no mechanism under it — and PROXY protocol is the same admission
   made at L4. Deliberately left as a question the reader carries: *what stops a client from writing
   that header itself?* Act V's `externalTrafficPolicy` and Act V 07b's `ipBlock` warning both pay it
   off; `the-whole-stack.md`'s existing XFF paragraph becomes recognition instead of first contact.

### 5.2 — `03b-the-stateful-firewall.md`

**Lab:** `docker run --rm -it --privileged nicolaka/netshoot` — deliberately **without**
`--network host`, and the lesson says why in a line: you are about to set a default-deny policy, so
you want a namespace you can throw away. It also quietly re-uses lesson 03's payoff, because the only
reason that container has internet access at all is the `MASQUERADE` rule the reader just read.

- **The wall.** Lesson 03 ended with `ufw` lying. Fine — write the rules yourself, on the right hook.
  `-P INPUT DROP`, then `ACCEPT` for the ports you meant to open. Then `curl example.com` hangs.
- **Sit in it.** The reply arrives with a *destination* port that is your own ephemeral source port,
  matching nothing. Try to fix it with what you have and feel both options fail: `--sport 80 -j ACCEPT`
  opens every port on the box to anyone who sets their source port to 80; `--dport 32768:60999` opens
  28,000 ports to the internet. **The lack, named:** a rule that sees only addresses and ports cannot
  tell a reply you asked for from a knock you didn't, because in the header they are identical.
- **Earned relief.** The kernel already wrote the difference down — Act III's table. The match is not
  a port, it is a question about the flow table: `-m conntrack --ctstate ESTABLISHED,RELATED`. One
  rule, no port numbers, and the entire class of problem closes.
- **`RELATED`, earned separately** by predicting whether an ICMP `port unreachable` for a tracked UDP
  probe counts as `ESTABLISHED` (it is not that flow) or as nothing (then `traceroute` could never
  work behind a firewall).
- **`DROP` vs `REJECT`, felt not told** — the same closed port, timed with `curl -w '%{time_connect}'`:
  `DROP` costs the client its full timeout, `REJECT --reject-with tcp-reset` costs it nothing. Then the
  callback that earns it: this is `nmap`'s `filtered` vs `closed` from
  [Act I 05b](networking-fundamentals/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md), read from
  the other side of the wire.
- **User chains as subroutines** — build a two-rule chain, jump to it, and use the counters to prove
  the fall-through: a non-terminal chain returns to *the rule after the jump* in its caller, and only
  `ACCEPT`/`DROP`/`REJECT` ends the walk. Named as the thing that makes `DOCKER-USER` and Act V's
  `KUBE-` tree readable rather than magic.
- **The shadow.** Default-deny on `INPUT` hardened *this machine*. The containers behind it are
  `FORWARD` traffic, whose policy is `ACCEPT` and whose first rule is Docker's. Two jobs, two hooks —
  which is Act V's NetworkPolicy and Stage 8's security groups, posed as a question.
- **Stage 8 seed, posed not answered:** you have now built a stateful firewall. Somewhere there is a
  cloud control that makes you write the return rule by hand. What would have to be *missing* from it
  for that to be necessary?

### 5.3 — `03c-when-nat-runs-out.md`

- **The wall.** `MASQUERADE` read like a free function. Two containers both picked source port 41000
  for the same destination; after translation both are `<host-ip>:41000 → <dst>:443`. So SNAT must
  rewrite the *port* too — and the reader derives the ceiling themselves from the demultiplexing key:
  with the source address pinned to the host and the destination pinned to one endpoint, the only free
  field is the source port. `sysctl net.ipv4.ip_local_port_range` prints the real number.
- **The number is worse than the range,** because conntrack rows outlive their connections (Act III
  again) — so the effective ceiling is the range divided by how fast you churn.
- **`--random-fully`,** earned as the fix for allocating from that space *without collisions*, and
  named as the flag kube-proxy carries.
- **Hairpin NAT.** Predict: from a second container, `curl <host-ip>:8080` at a published port on the
  same bridge. The DNAT fires, the packet is forwarded back out the bridge it arrived on, and the
  target replies **directly** to the caller — from an address the caller never dialled, so the caller's
  kernel discards it. The fix is to SNAT the hairpinned packet as well, which is what `hairpin_mode`
  and kubelet's `hairpinMode` are.
- **`mangle` — the third table.** `filter` decides, `nat` rewrites, `mangle` **annotates**: a mark is
  metadata that exists only inside this kernel and never appears on the wire. Its whole point is that
  it is the join key to something the reader already owns — `ip rule add fwmark 1 table 100`, Act II's
  policy routing, now driven by a firewall match.
- **`-t raw` / `NOTRACK`,** earned from Act III's ceiling: given that every flow costs a row and the
  ceiling is finite, can a flow opt out? Yes — at the price of NAT and of every `--ctstate` match for
  that flow, which is *why* `raw` sits at a priority before conntrack rather than inside it.
- **Forward question:** everything so far rewrote headers. What do you do about traffic that was never
  addressed to you at all?

### 5.4 — `03d-the-transparent-proxy.md`

- **The wall.** Act III's proxies all required the client to *address* them. You do not own these
  clients — they are containers someone else built, dialling `example.com` directly — and you must
  route every outbound connection through your own proxy without editing one of them.
- **Sit in it.** DNAT the packet to the proxy's port. The connection arrives. Now the proxy asks the
  only question that matters — *which server was this client trying to reach?* — and finds it cannot
  answer: the destination was rewritten before `accept()` ever returned, so the socket's local address
  is the proxy's own. **You destroyed the one field you needed in order to do the job.**
- **Two rivals, and the reader earns both.**
  - `-j REDIRECT` plus `getsockopt(SO_ORIGINAL_DST)` — the kernel *did* keep it, in the conntrack row,
    and hands it back through a socket option. conntrack's third role: not a NAT ledger, not a firewall
    oracle, but **an API**. Written as a short `python3` listener, in the spirit of Act I's `minihttp`:
    the reader becomes the proxy rather than configuring one.
  - `TPROXY` — do not rewrite at all. Mark the packet, `ip rule` it to a local table, and let a socket
    bound with `IP_TRANSPARENT` accept a connection addressed to somebody else. This is why 5.3 comes
    first: without `MARK` and `ip rule` this is an incantation.
  - The trade, stated as a trade: `REDIRECT` is one rule and loses the source address on the way out;
    `TPROXY` keeps the whole four-tuple and costs a routing table.
- **Recognition, not instruction.** An init container writing `REDIRECT` rules into a Pod's netns so
  everything lands on a sidecar's port *is* a service mesh. The reader will have built it before they
  are told the name.
- **The shadow.** A proxy the client cannot detect and did not choose is Act II's ARP shadow with
  better tooling — and the only reason it cannot read the bytes is the sealed lock from Act III lesson
  05, which is Act VIII's business. Posed, not resolved.

## 4. Obligations per unit

Items numbered as in [`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md) §4.

| Item | Phase 5 disposition |
|---|---|
| 1, 2, 3 (predict-first, ladder + milestone, links) | per lesson, hard-checked |
| 4 `LESSON-INDEX.md` | three new lines under Act IV |
| 5 act README nav + four-file shape | Act IV README numbered list re-numbered 6→9; `03`→`03b`→`03c`→`03d`→`04` footer chain rewired at both ends |
| 6–10 (tool roster, `capabilities.json`, tool page, `SHELL_COMMANDS`, per-act commands) | **not triggered** — no new tools, by design |
| 11 drills | Act IV `diagnose.md` drills 10–12 + `drills/act-4/{10,11,12}.sh` + verifier; one per new lesson, symptom-first: a hung `curl` that is a `DROP`, a published port that answers from everywhere except the container beside it, a proxy that cannot name the destination |
| 12 exam-prep | Route B step 1 is `act-4-one-pretends-many/**` so it absorbs the files, but its **printed word and drill counts go stale** — regenerate; CKA domain map gains no row (netfilter depth is not examined), CKS gains none |
| 13 `remeasure.py --write` | after all four units |
| 14 `technical-accuracy-checker` + `learner-simulator` | **deferred to a single pass after all four units are drafted**, at the reader's explicit choice. Until that pass runs, no unit here may be described as shipped, and the `LESSON-INDEX` build-status note must not claim these were run. |
| 15 under 10,000 words | all four comfortably under; Act III 04 lands ~5,100 |
| — `routes.json` | **Route C step 6 lists `03-*.md` explicitly, which does not match `03b-`.** All three new globs must be added or `routes.reorder-covers-course` fails. This is the one machine-checked trap in the whole phase. |

## 5. What this phase deliberately does not add

- **eBPF/XDP as a rival to netfilter.** Act V lesson 03 already earns Cilium as the fix for netfilter's
  linear walk and L3/4 blindness, at the point where the reader has thousands of Services to feel it
  with. Hoisting it here would hand over the answer before the pain.
- **`nftables` native syntax as a teaching grammar.** Lesson 03 already establishes that `iptables` is
  a front-end and that `nft list ruleset` is the honest read. Teaching the same rules twice in two
  grammars is words, not understanding.
- **Firewall products** (`firewalld`, `ufw` beyond lesson 03's shadow, cloud NGFW). Each is a front-end
  over the hooks the reader can now read directly, which is the whole point of reading the table
  instead of the tool.

## 6. What shipping actually requires from here

Everything below is done: the four units, the three drills and verifiers (`drills/act-4/{10,11,12}.sh`,
answers stored as hashes), three recall questions, the nav chain rewired at both ends
(`03 → 03b → 03c → 03d → 04`), the Act IV README, the `LESSON-INDEX` entries, Route C's step-6 globs and
drill list, Route B's step-1 figures and its optional-track row, the Stage 6 bullet in the map, and both
published-count regenerations. `python3 -m harness` reports **all 25 invariants holding**.

What is **not** done, and what must happen before any of this is described as shipped:

1. **`technical-accuracy-checker` over all four units.** Every command block run in the real lab image.
   The highest-risk claims, in order: `SO_ORIGINAL_DST` on an `OUTPUT`-`REDIRECT`ed, locally-originated
   flow (03d's first experiment turns on it); the exact `curl` exit codes and timings quoted for
   `DROP` (28) versus `REJECT` (7); whether `iptables -P INPUT DROP` in a plain `--privileged` container
   really fails at *name resolution* first, which depends on that container's resolver; the `--local-port
   41000` collision in 03c actually producing a remapped reply tuple; `TPROXY` inside a nested namespace
   with `IP_TRANSPARENT`; and whether the three drill reproduce-blocks induce their symptom on a first run.
2. **`learner-simulator` over all four**, against the anchor knowledge each claims. The specific River
   risk to check: 03d leans on `mangle` + `MARK` + `ip rule` from 03c and on `CONNECT`/`X-Forwarded-For`
   from the Act III extension — if a reader takes Route B, they hit Act IV (step 1) *before* Act III
   (step 2), so 03d's Act III callbacks must degrade to forward references rather than dependencies.
   Check that they do; if they do not, the fix is to weaken the callback, not to move the lesson.
3. **Correct the expected outputs against what happened**, then delete the caveat paragraph this phase
   added to `LESSON-INDEX.md`.
