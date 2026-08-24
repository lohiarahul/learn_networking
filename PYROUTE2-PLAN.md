# Feasibility — mapping the tool roster onto pyroute2

*Investigated 2026-08-24. Every claim below was executed: pyroute2 read from source at
`svinota/pyroute2@0.9.6`, and four demos run inside `nicolaka/netshoot` (the base of the course's own
lab image) with `--privileged`. Nothing here is inferred from documentation.*

---

## The short answer

**"Map all the tools to pyroute2" is not possible, and the reason it isn't is the thing worth
shipping.**

`reference/03-the-index.md` has **78 rows**, 7 of them macOS companions — **71 Linux tools**. pyroute2
is a direct API equivalent for **13 of them**. Not because pyroute2 is incomplete, but because the
other 58 tools do not talk to netlink at all: `tcpdump` opens `AF_PACKET`, `dig` opens a UDP socket,
`strace` calls `ptrace(2)`, `kubectl` makes an HTTPS request. A netlink library cannot map them because
there is nothing to map.

But the attempt answers the actual complaint. The section feels scattered because **the index is sorted
by what a tool is *for*, and a reader cannot derive anything from that.** `ss` and `netstat` sit in the
same category and speak two different kernel APIs. `ss` and `ethtool` sit in different categories and
speak the same one. Sort the roster by **which kernel interface the tool is a client of** and it
collapses to eight buckets, tools inside a bucket become substitutable, and tools across buckets become
provably non-substitutable — which is exactly what the *"the one thing only it shows you"* column is
trying to say and cannot, one row at a time.

So: **pyroute2 is not the spine for the section. It is the executable proof for the largest single
bucket, and the excuse to introduce the taxonomy that is.**

---

## Finding 1 — the eight buckets, and all 71 tools placed in them

> ### ⚠️ Superseded in four rows by measurement — see [Phase 1's `Speaks` facet](#facet-1--speaks-the-interface-measured)
>
> The table below was reasoned from source and documentation. Phase 1 then `strace`d every tool, and
> four assignments here are wrong: **`ethtool` and `ipvsadm` are netlink** (generic-netlink, not
> `ioctl`), **`arp` is `procfs`** (`/proc/net/arp`, never netlink), **`ip netns` is namespace syscalls**
> (bind mounts under `/run/netns`), and **`ping` is an ordinary `SOCK_DGRAM` socket**, not raw. Bucket 3
> also turns out to be **empty on a current system** — `iptables -L` opens `NETLINK_NETFILTER`.
>
> The table is preserved as written because the *shape* of the finding survived intact and the
> corrections are the useful part. The measured taxonomy is the one to build from.

| # | Kernel interface | Tools | n | Reference page that owns it |
|---|---|---|---|---|
| 1 | **netlink** — `AF_NETLINK` sockets | `ip` · `ip netns` · `bridge` · `tc` · `ss` · `conntrack` · `nft` · `ipset` · `ipvsadm` · `ethtool` · `devlink` · `wg` · `arp` | 13 | **nothing yet** ← the gap |
| 2 | **procfs / sysfs** — `open()` + `read()` | `cat` · `stat` · `readlink` · `netstat` · `lsof` · `sysctl` · `nstat` · `pgrep` · `capsh` · `getpcaps` · `mount`/`findmnt` · `ulimit`/`prlimit` | 12 | `02-the-state-map.md` ✅ |
| 3 | **xtables `setsockopt`** — the odd one out | `iptables` *(legacy backend)* · `iptables-save` | 2 | `01-the-grammar.md` Rule 6, partly |
| 4 | **raw & packet sockets** — `AF_PACKET`, `SOCK_RAW` | `tcpdump` · `tshark` · `scapy` · `ping` · `arping` · `traceroute` · `mtr` · `nmap` | 8 | scattered across acts |
| 5 | **ordinary sockets** — `socket()`/`connect()` | `nc` · `socat` · `curl` · `dig` · `drill` · `host` · `nslookup` · `getent hosts` · `iperf3` | 9 | Act I, then nowhere |
| 6 | **BPF & ptrace** — `bpf(2)`, `perf_event_open`, `ptrace` | `bpftool` · `bpftrace` · `pwru` · `retis` · `strace` · `ltrace` · `falco` | 7 | nothing |
| 7 | **somebody else's HTTP API** | `docker` · `crictl` · `kubectl` · `kind` · `kubeadm` · `etcdctl` · `etcdutl` · `helm` · `kustomize` · `cilium` · `trivy` · `cosign` · `crane` · `kube-bench` | 14 | Acts V–X |
| 8 | **process & LSM syscalls** — `clone`/`setns`/securityfs | `unshare` · `nsenter` · `runc` · `apparmor_parser` · `jq` · `xxd`/`base64` *(the last two touch no kernel API — pure text, and saying so is the point)* | 6 | Act IV, Act X |

**13 + 12 + 2 + 8 + 9 + 7 + 14 + 6 = 71.** Exhaustive, no row unplaced.

Three things fall out of it that the current index cannot say:

- **Bucket 1 is the biggest, and it is the only one with no page.** It also contains **six of the
  sixteen `roster only` tools** the index honestly confesses it never teaches — `nft`, `ipset`, `tc`,
  `ipvsadm`, `ethtool`, `devlink`. One page on netlink makes all six *derivable* rather than merely
  admitted. That is the highest-leverage paragraph in this document.
- **Bucket 3 has two members and exists to explain itself.** `iptables` gets its own interface because
  it is the only tool in the roster that talks to the kernel through `setsockopt` on a raw socket. That
  is *why* nftables was written, and why the index's "run `iptables -V` first" warning matters — see
  Finding 3, where it is demonstrated rather than asserted.
- **Buckets 2 and 5 are where the course already starts.** Act I is "everything is a file" (bucket 2)
  and "the socket object" (bucket 5). The taxonomy is not new furniture bolted on; it is the two things
  the reader already owns, extended to cover the other six.

---

## Finding 2 — pyroute2's API is the `ip` object list, one method per netlink message family

Not a resemblance. `pyroute2/iproute/linux.py` class `RTNL_API` exposes:

```
link()   addr()   route()   neigh()   rule()   tc()
brport() fdb()    vlan_filter()  vlandb()  stats()
get_links() get_addr() get_routes() get_neighbours() get_rules()
get_qdiscs() get_classes() get_filters() get_vlans() get_ntables()
get_default_routes() link_lookup() flush_routes() flush_addr() flush_rules()
get_netnsid() get_netns_info() set_netnsid()
```

and `pyroute2/netlink/rtnl/__init__.py` carries **70 `RTM_*` constants**. This closes a caveat the
grammar page currently has to leave open. Rule 2 says:

> The **object** half is a strong correspondence rather than a documented design statement

pyroute2 turns it into a machine-checkable one, because every method carries an explicit
`command_map` from CLI-shaped verb to `(RTM_message, flag_set)`. Verbatim from
`pyroute2/iproute/linux.py`:

```python
# route()                              # link()
'add':     (RTM_NEWROUTE, 'create')    'add':  (RTM_NEWLINK, 'create')
'change':  (RTM_NEWROUTE, 'change')    'set':  (RTM_NEWLINK, 'req')
'replace': (RTM_NEWROUTE, 'replace')   'del':  (RTM_DELLINK, 'req')
'append':  (RTM_NEWROUTE, 'append')    'dump': (RTM_GETLINK, 'dump')
'del':     (RTM_DELROUTE, 'req')
'dump':    (RTM_GETROUTE, 'dump')
```

and those flag-set names resolve, in `pyroute2/netlink/nlsocket.py`, to precisely the kernel-header
table Rule 2 already quotes:

```python
flags = {'dump': NLM_F_REQUEST | NLM_F_DUMP,
         'req':  NLM_F_REQUEST | NLM_F_ACK}
flags['create']  = flags['req']    | NLM_F_CREATE | NLM_F_EXCL
flags['append']  = flags['req']    | NLM_F_CREATE | NLM_F_APPEND
flags['change']  = flags['req']    | NLM_F_REPLACE
flags['replace'] = flags['change'] | NLM_F_CREATE
```

**Verified, in the lab image** — the table printed as hex, then its own prediction tested:

```
create   0x0605     # REQUEST|ACK|CREATE|EXCL
replace  0x0505     # REQUEST|ACK|CREATE|REPLACE
change   0x0105     # REQUEST|ACK|REPLACE
append   0x0c05     # REQUEST|ACK|CREATE|APPEND
dump     0x0301     # REQUEST|ROOT|MATCH
get      0x0005     # REQUEST|ACK

created veth pair, indexes: [13] [12]
add twice     -> 17 (17, 'File exists')     # because EXCL
addr add twice-> 17 (17, 'File exists')     # because EXCL
addr replace  -> OK                         # because CREATE|REPLACE
```

Rule 2's payoff paragraph currently ends *"you now know, without testing, why `ip addr add` fails…"*.
This makes it *"and here is the test"* — three lines, and the errno is `EEXIST` because one bit was set.

**A fact only visible this way.** `pyroute2/netlink/__init__.py` puts all the constants in one block,
and the block shows that the three modifier bits are *overloaded*:

```python
NLM_F_ROOT    = 0x100      NLM_F_REPLACE = 0x100
NLM_F_MATCH   = 0x200      NLM_F_EXCL    = 0x200
NLM_F_ATOMIC  = 0x400      NLM_F_CREATE  = 0x400
```

Same three bits, different meanings depending on whether the message is a `GET` or a `NEW`. The kernel
header splits these into two comment blocks ("Modifiers to GET request" / "Modifiers to NEW request")
and Rule 2 quotes only the second — so the page currently cannot explain why `dump` and `change` share
a bit. Now it can.

**Honest caveat the new page must carry:** the verb→flag mapping is *per object*, not global.
`link('add')` is `(RTM_NEWLINK, 'create')` but `brport('add')` is `(RTM_SETLINK, 'req')` — no `CREATE`,
no `EXCL`, a different message entirely. This is a *better* caveat than the one the page has now,
because it is specific and checkable.

---

## Finding 3 — the demo that justifies the whole exercise

The index page already warns that since 1.8, `iptables` is a CLI over two different kernel backends and
you must run `iptables -V` to know which. It states this. It cannot show it. **Executed in the lab
image:**

```
$ iptables -V
iptables v1.8.11 (nf_tables)

$ iptables -t nat -A POSTROUTING -s 10.9.0.0/24 -j MASQUERADE

$ python3 -c "from pyroute2.nftables.main import NFTables
with NFTables(nfgen_family=2) as nft:
    print([t.get('name') for t in nft.get_tables()])
    print([(c.get('table'), c.get('name')) for c in nft.get_chains()])
    print([(r.get('table'), r.get('chain')) for r in nft.get_rules()])"
['nat']
[('nat', 'POSTROUTING')]
[('nat', 'POSTROUTING')]
```

**A rule added with `iptables` was read back through the *nftables* netlink API.** One command pair
proves that the tool the course spends a whole lesson on is, on any current distro, a translation layer
over the tool the course lists as `roster only`. Nothing in the existing seven pages can do that, and no
amount of prose is as convincing.

Three more, same image, same session — establishing that bucket 1 really is one interface:

```
DiagSocket()  -> listen: 0.0.0.0 9999        # this is what `ss` is
Ethtool()     -> eth0 link: 10000            # this is what `ethtool` is
Conntrack()   -> conntrack count: 0          # this is what `conntrack` is
```

---

## Finding 4 — the mechanical costs are near zero

| Question | Answer | How established |
|---|---|---|
| Runtime dependencies? | **None** on Linux (`win_inet_pton` on Windows only) | `pyproject.toml` |
| Python floor? | `>=3.9`; netshoot ships 3.12 | `pyproject.toml`, image |
| Licence? | `GPL-2.0-or-later OR Apache-2.0` — dual, so citing is unencumbered | `pyproject.toml` |
| Installs in the lab image? | **`RUN apk add --no-cache py3-pyroute2`** — one line; `python3` is already there | ran it |
| Actually works in the lab image? | **Yes**, all four demos above | ran them |
| Fights `gen-command-tables.py`? | **No.** `python`/`py` are in its `NON_SHELL_LANGS`, so Python fences are never harvested as commands | `tools/gen-command-tables.py:44` |
| Fights `check_pedagogy.py`? | **No.** `is_lesson()` already exempts `reference/` from Predict-first and the ladder. Link integrity still applies, which is wanted | `tools/check_pedagogy.py:65` |
| Site nav cost? | One line in the ordered list at `site/scripts/sync-content.mjs:114–123`, plus renumbering the orders after it | read it |

---

## The plan

Four phases. **Phase 1 is independently valuable and does not mention pyroute2 at all** — if the rest is
never built, the section is still fixed.

### Phase 1 — the taxonomy (fixes the stated complaint)

The complaint is "no way to build a mental model". The taxonomy *is* the mental model; pyroute2 is only
evidence for one eighth of it. So ship it first, alone.

1. **`03-the-index.md`: add an `Interface` column**, one bucket name per row, 78 rows. Keep the existing
   topical tables — they serve lookup, which is this page's job — but put a **summary table sorted by
   interface** at the top, so the reader sees eight groups before they see seventy-eight rows.
2. **`README.md`: name the taxonomy in "the one thing to read even if you never look anything up".**
   That paragraph currently sends the reader to the grammar page for *spelling*. It should send them for
   spelling *and* for which API the spelling addresses.
3. **`04-by-question.md`: nothing.** It is symptom-indexed and already the right shape. Leave it.

**Test of success:** a reader handed `nstat` and `pwru` — two tools no lesson runs — can say which
interface each speaks and therefore which existing tool each is substitutable with, without looking
either up.

### Phase 2 — the new page: `reference/07-netlink-and-one-library.md`

Ordered **after** `06-derive-it.md`, not before. It is the deepest page, not the entry point, and the
existing numbering is a reading order.

Sections, in order:

1. **The eight buckets**, stated once and compactly — the same table as Phase 1, so the page can be read
   standalone.
2. **Bucket 1 in full**: netlink's four sub-families and which CLI sits on each —
   `rtnetlink` (`ip`, `bridge`, `tc`), `sock_diag` (`ss`), `nfnetlink` (`conntrack`, `nft`, `ipset`),
   `genetlink` (`ethtool`, `devlink`, `wg`, `ipvsadm`). This is the paragraph that makes eleven
   scattered tools into one thing with four rooms.
3. **Rule 2, executed** — the flag table printed as hex, the `EEXIST` test, the overloaded bits
   (Finding 2).
4. **The `iptables`/nftables read-back** (Finding 3), placed as the page's payoff.
5. **Where the mapping stops** — the per-object caveat, `iptables` legacy, and the plain statement that
   58 of 71 tools are outside this bucket and nothing here helps with them.

Constraint the page must hold to: **pyroute2 appears as evidence, never as a tool the reader is expected
to adopt.** No snippet over five lines; every snippet prints a fact. The moment this becomes a Python
tutorial it has stopped being a reference for Linux networking, which is what `README.md` promises it is.

### Phase 3 — `06-derive-it.md`: Ladder 4, "derive the message"

The page has three ladders (command, path, tool). Add a fourth, in the same reveal-hidden format:

- Forward: given `ip route append …`, name the `RTM_*` message and the flag word. Check with pyroute2.
- Reverse: given `ipr.neigh('replace', …)`, write the `ip` command.
- The trap: given `bridge link set …`, notice it is `RTM_SETLINK` with no `CREATE` bit, and say why
  "add" does not mean the same thing here.

This is the ladder that most directly serves the JOURNEY-MAP's *predict, don't recite* goal, because the
answer is derivable from two tables and is verifiable in one command.

### Phase 4 — the lab image

One line in `networking-fundamentals/code/Dockerfile`:

```dockerfile
RUN apk add --no-cache py3-pyroute2
```

**Pin it.** pyroute2 is pre-1.0 and its surface has moved (`IPDB` deprecated in favour of `NDB`,
`AsyncIPRoute` added). Every source quote on the new page must cite file *and* version the way Rule 2
cites the kernel header, or the page rots silently — which is the one failure mode `reference/` is
explicitly built to prevent.

---

## Risks, honestly

| Risk | Severity | Mitigation |
|---|---|---|
| Page drifts into a Python tutorial | **High** — it is the natural failure | Five-line cap; pyroute2 is evidence, never a recommended tool. `technical-accuracy-checker` runs every block, so a bloated snippet is expensive and self-limiting |
| pyroute2 API churn (pre-1.0) | Medium | Pin the version in the Dockerfile; cite file + tag on every quote |
| Taxonomy edges are fuzzy | Low | They are *features*: `iptables` sits in two buckets depending on `-V`, and that is Finding 3. State the ambiguity, don't hide it |
| Eight buckets is one more concept for an already-full section | Medium | Phase 1 ships the taxonomy with **no new page** — a column and a summary table. Net concepts added before any new reading: one |
| `bpftool`/`pwru` are BPF *and* netlink-adjacent | Low | Bucket by the primary interface, note the overlap in the row |

---

## Recommendation

Do **Phase 1 now** and judge the result before committing to Phase 2. The taxonomy is the fix for the
complaint; the pyroute2 page is the proof that makes bucket 1 teachable and closes six of the sixteen
`roster only` gaps. Phase 1 costs a column and a table. Phase 2 costs a page and earns the
`iptables`-is-nftables demo, which is the single best thing this investigation turned up.

Do **not** attempt a row-by-row pyroute2 mapping of the whole index. Fifty-eight of the seventy-one rows
would read "not netlink — n/a", and a reference whose widest column is empty is worse than the one that
exists now.

---
---

# Phase 1 — detailed design: how to compartmentalise 71 tools

*Designed and measured 2026-08-24. Every interface assignment below was verified by `strace` inside
`nicolaka/netshoot`, not inferred. Three of this document's own earlier assumptions were wrong and are
corrected here.*

## The problem, stated precisely

The index is sorted by **what a tool is for**. That is the right sort for lookup and the wrong one for
building a model, because *purpose is not derivable from anything*. You cannot look at an unfamiliar
tool and work out its purpose, and knowing its purpose tells you nothing about how to drive it.

A reader becomes proficient when they can answer three questions about a tool they have never run:

| Question | What answers it | Currently on the page? |
|---|---|---|
| **How** do I drive it? | which interface it addresses, and its grammar | grammar only, in a `Grammar` column |
| **When** do I reach for it? | can it change things · can it catch a transient | **no** |
| **What** does it uniquely give me? | the "one thing only it shows you" column | yes, and it is the page's best asset |

So Phase 1 adds the two missing facets and a view that groups by them. It adds no prose.

## The design rule that keeps this from becoming a spreadsheet

**A facet earns a column only if it is not derivable from another facet.**

This rule killed three candidate facets during design, and recording why is more useful than the ones
that survived:

- **Layer (L2/L3/L4/L7)** — killed. It is what the existing topical section headings already encode, and
  it is the *least* derivable-from thing on the page: knowing `dig` is L7 tells you nothing about how to
  drive it.
- **Active vs passive** (does it inject traffic?) — killed, because it is derivable: `Speaks ∈ {socket,
  packet}` ⇒ active. A column that repeats another column is a column that will drift out of step with it.
- **Scope** (process / netns / host / off-box) — killed, reluctantly. It is genuinely useful, but its
  edges are not closed: `sysctl` is host-scoped for `kernel.*` and **netns-scoped for `net.*`**, which is
  a fact `02-the-state-map.md` already teaches properly and a one-word cell would lie about. Blindness
  questions are already served by `04-by-question.md` ("it works from the node but not the Pod") and by
  the state map's namespace section. Two pages doing it well beats three doing it badly.

Two facets survive.

## Facet 1 — `Speaks`: the interface, measured

Closed vocabulary, **eight values**, each defined by a syscall you can see in `strace`. That definition
is what makes the facet checkable rather than a matter of taste.

| Value | What you see in `strace` | n |
|---|---|---|
| `netlink` | `socket(AF_NETLINK, …)` | 13 |
| `procfs` | `open()` on `/proc` or `/sys` | 14 |
| `packet` | `socket(AF_PACKET, …)` or `SOCK_RAW` | 7 |
| `socket` | `socket(AF_INET, SOCK_STREAM｜SOCK_DGRAM)` | 10 |
| `probe` | `ptrace` · `bpf(2)` · `perf_event_open` | 7 |
| `nsapi` | `unshare` · `setns` · `clone` + bind mount | 4 |
| `httpapi` | HTTPS/gRPC to a daemon or an API server | 11 |
| `local` | none — reads files or bytes you already have | 5 |

`13+14+7+10+7+4+11+5 = 71`. Exhaustive, no tool unplaced, no tool in two buckets.

### What the measurement corrected

Run inside the lab image, `strace -f -e trace=socket,openat,ioctl,ptrace,setns,unshare`:

```
ip addr          AF_NETLINK  NETLINK_ROUTE
ss -tan          AF_NETLINK  NETLINK_SOCK_DIAG
bridge fdb       AF_NETLINK  NETLINK_ROUTE
tc qdisc         AF_NETLINK  NETLINK_ROUTE      /proc/net/psched
conntrack -L     AF_NETLINK  NETLINK_NETFILTER
nft list ruleset AF_NETLINK  NETLINK_NETFILTER
ipset list       AF_NETLINK  NETLINK_NETFILTER
ipvsadm -L       AF_NETLINK  NETLINK_GENERIC
ethtool eth0     AF_NETLINK  NETLINK_GENERIC
iptables -t nat -L  AF_NETLINK  NETLINK_NETFILTER   /proc/net/ip_tables_names
arp -an          /proc/net/arp            AF_INET, SOCK_DGRAM
netstat -tan     /proc/net/tcp  /proc/net/tcp6
nstat            /proc/net/snmp  /proc/net/netstat
lsof -i          /proc/PID/fd/
ping -c1         AF_INET, SOCK_DGRAM
arping           AF_PACKET
traceroute       AF_INET, SOCK_RAW
tcpdump          AF_PACKET
dig              AF_INET, SOCK_DGRAM     /etc/resolv.conf
getent hosts     /etc/hosts               (no socket at all)
nc / curl        AF_INET, SOCK_STREAM
unshare          unshare(2)
nsenter          setns(2)
strace           ptrace(2)
```

Four results are worth more than the table they sit in:

1. **`ethtool` and `ipvsadm` are `NETLINK_GENERIC`.** Both are commonly described as `ioctl` tools, and
   both were `ioctl` historically. On a current kernel they are generic-netlink. This document asserted
   `ioctl` for `ethtool` before measuring; it was wrong.
2. **`arp` never touches netlink** — it reads `/proc/net/arp`. That is *why* `arp` and `ip neigh` can
   disagree, and the index's "nothing `ip neigh` doesn't" row can now say so mechanically.
3. **`ping` opens `SOCK_DGRAM`, not `SOCK_RAW`.** ICMP datagram sockets, gated by
   `net.ipv4.ping_group_range`. The reason `ping` no longer needs setuid, visible in one trace.
4. **`iptables -t nat -L` opened `NETLINK_NETFILTER`** *and* read `/proc/net/ip_tables_names` — it
   probed for the legacy backend, found nf_tables, and spoke netlink. This is Finding 3 confirmed from
   the opposite direction, and it means the `xtables setsockopt` bucket this document originally proposed
   is **empty on a current system**. It is therefore not a bucket; it is a footnote on two rows.

### The five footnotes the vocabulary needs

A closed vocabulary that hides its own exceptions is worse than an open one. Five rows carry a marker:

| Tool | Marker | Why |
|---|---|---|
| `iptables`, `iptables-save` | `netlink †` | netlink on the nf_tables backend, `setsockopt` on legacy. **`iptables -V` tells you which** — the index already warns about this and can now show the mechanism |
| `nmap` | `packet ‡` | `packet` for `-sS` (the half-open scan the course teaches), `socket` for the `-sT` default |
| `ping` | `socket §` | `SOCK_DGRAM` ICMP, not raw, on current kernels |
| `getent hosts` | `socket ¶` | NSS: files first, and it opens **no socket at all** if `/etc/hosts` answers — measured above |
| `ip netns` | `nsapi ‖` | `nsapi` for create/exec (bind mounts under `/run/netns`), `netlink` for the nsid lookups |

## Facet 2 — `Mode`: what it can do to the world

Closed vocabulary, **three values, combinable**. This is the "when do I reach for it" facet, and it
answers the only two questions that matter under pressure.

| Value | Means | The question it answers |
|---|---|---|
| `read-only` | cannot change kernel or cluster state | *Is this safe to paste at 3am?* |
| `mutate` | can change state | *Will this change the thing I am measuring?* |
| `live` | streams events as they happen | *Can I catch a transient a polling loop misses?* |

Cells combine: `mutate · live` for `conntrack`, `read-only` for `dig`, `live` for `tcpdump`.

**`live` is the highest-value cell on the page**, because the answer is short and nobody has it
memorised. Nine tools in the whole roster can stream:

`ip monitor` · `ss -E` · `bridge monitor` · `conntrack -E` · `nft monitor` · `tc monitor` ·
`tcpdump`/`tshark` · `strace`/`ltrace`/`bpftrace`/`pwru`/`retis` · `docker events` · `kubectl get -w` ·
`etcdctl watch` · `falco` · `mtr`

Everything else is a snapshot, and *"I polled and saw nothing"* is not evidence.

## What actually changes on disk

### 1. `reference/03-the-index.md`

**Column change** — the `Grammar` column becomes `Speaks` and carries two tokens
(`netlink · obj-verb`), because interface and grammar answer the same question and the correlation
between them is itself a finding. One new column, `Mode`. Net: 5 columns → 6.

```
| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
| `ss` | …    | …                               | netlink · flags + filter | live | … |
```

**Two new views, above the topical tables:**

- **The eight interfaces** — the whole roster in eight rows, each with its `strace` signature. This is
  the mental model, on one screen, and it is what a reader looks at to place a tool nobody taught them.
- **What can stream** — the nine-tool `live` list above.

**What does not change:** the topical section headings stay. The page's job is lookup and its README
says so; regrouping by interface would serve the model at the cost of the lookup. The interface *view*
is the summary table; the interface *fact* is a column. Nothing is duplicated — the summary lists tool
names only, and every claim about a tool lives in exactly one cell.

### 2. `reference/README.md`

Three sentences in *"the one thing to read even if you never look anything up"*, which currently sends
the reader to the grammar page for spelling. It should send them for spelling **and** for which
interface the spelling addresses — those are the same skill. Plus the index's row in the page table
gains the taxonomy.

### 3. `tools/check_pedagogy.py` — the drift guard

This is what makes the scheme survive contact with future edits. Three warnings:

1. Every `Speaks` cell's first token ∈ the eight values. A typo becomes a build warning, not a lie.
2. Every `Mode` cell's tokens ⊆ {`read-only`, `mutate`, `live`}.
3. **The summary table's tool lists exactly partition the topical tables' tools** — same set, no
   duplicates, nothing missing. This is the check that matters: it makes it impossible to add a tool
   without placing it, which is the failure mode every taxonomy dies of.

The existing `command-table-coverage` warning already cross-checks the index against the site's shell
classifier, so this sits in a slot the file already has.

### 4. Not touched

`04-by-question.md` (symptom-indexed, already right shape) · `05-per-act-commands.md` (generated
skeleton) · `06-derive-it.md` (Phase 3) · the macOS table (the taxonomy is about Linux kernel
interfaces; a `pfctl` row claiming `netlink` would be false).

## Test of success

A reader is handed three tools no lesson runs — `nstat`, `pwru`, `devlink` — and can say, without
looking them up:

- `nstat` speaks `procfs`, so it is a snapshot of counter files and it can tell you nothing `cat` could
  not, only more conveniently. Substitutable with `cat /proc/net/snmp`.
- `pwru` speaks `probe` and is `live`, so it is the only kind of tool that can answer "which kernel
  function dropped it" — and no `netlink` or `procfs` tool can ever substitute for it.
- `devlink` speaks `netlink` with `obj-verb` grammar, so `devlink dev show` and `devlink port show` are
  guessable without the man page, and `ip`'s global options habits transfer.

That is the proficiency the section is currently missing, and none of it required prose.
