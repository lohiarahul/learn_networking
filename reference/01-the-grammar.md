# The grammar — how to guess a command you were never taught

The acts teach you about fifty commands. There are thousands, and the ones you will need on the worst
day of your career are the ones nobody showed you.

This page is the way out of that. The tools were not named at random: they were built by people
following conventions, and most of those conventions are still visible in the spelling. Learn the
handful of rules below and a large class of commands stops being something you remember and becomes
something you **work out** — including commands that did not exist when you learned the rule.

> **Who this is for.** It assumes you have worked Acts I–IV, so `/proc/net/tcp`, namespaces, veth
> pairs, `iptables` and `conntrack` are already yours. A few examples reach into Acts V–X or name a tool
> the course never runs; those are marked where they appear.

Two honesty notes, because they set the ceiling on everything here.

**Names are not actually guessable, and the research is brutal about it.** Furnas and colleagues asked
people to name the same operation and found that *"in every case two people favored the same term with
probability &lt; 0.20"* — one designer's favourite word produces 80–90% failure rates. So the claim of this
page is **not** "systematic names can be guessed from first principles". It is the weaker, achievable
one: *a consistent grammar can be learned once and then applied to things you have not seen.* You still
have to be told the grammar. You do not have to be told each command.

**Every rule here is followed by the specific place it breaks**, because a rule you trust too far is
worse than no rule. Where a claim is popular but unsourced, this page says so rather than repeating it.

---

## Rule 1 — Modern tools are `TOOL OBJECT VERB`

The old Unix tools were one command per job: `ifconfig` configured interfaces, `route` edited routes,
`arp` edited the ARP cache. Three tools, three flag vocabularies, three man pages.

Then the design changed. The tool became a *namespace*, the noun moved into the first argument, and the
verb followed it:

```
ip      link     add
bridge  fdb      show
bpftool prog     show
docker  network  inspect
```

**Why this matters more than it looks:** in an object-verb tool you do not learn N commands. You learn
one object list and one verb list, and every valid combination is a command you can now write. That is a
multiplication table, not a vocabulary list.

### The worked example: `ip`

`ip` is the tool this course leans on hardest — 213 invocations across the acts, more than any other
networking command — so it is worth knowing structurally rather than by the five subcommands the lessons
happen to use.

Its synopsis, verbatim from `man 8 ip`:

```
ip [ OPTIONS ] OBJECT { COMMAND | help }
```

**The object list is closed and short.** All of it, from the same man page:

```
address    addrlabel  fou        help       ila        ioam       l2tp
link       macsec     maddress   monitor    mptcp      mroute     mrule
neighbor   neighbour  netconf    netns      nexthop    ntable     ntbl
route      rule       sr         tap        tcpmetrics token      tuntap
vrf        xfrm
```

That is about 27 distinct objects — the list above counts `neighbor`/`neighbour` and `ntable`/`ntbl`
twice, and `help` is not an object. **The course uses five of them** (`addr`, `link`, `route`, `neigh`,
`netns`). The other twenty-two are not more advanced; they are the same grammar pointed at a different
kernel table.

**The verb list repeats across objects.** Most objects accept some subset of:

```
add   del|delete   show|list|lst   set   change   replace   append   flush   get   help
```

So `ip route flush`, `ip neigh flush`, `ip addr flush` and `ip link set` are all commands you can write
without ever having seen them.

### Rule 1a — any unambiguous prefix works, and two prefixes are traps

You have already been typing `ip addr` and `ip neigh`, which are not in the object list above — the full
words are `address` and `neighbour`. That works because `ip` matches on **prefix**, not on the whole
word, taking the **first match in its internal table order**. So `ip a`, `ip r`, `ip l`, `ip n` are all
legal, and so is `ip addr lst`.

Two prefixes resolve somewhere surprising, because table order — not usefulness — decides:

| You type | You get | You probably meant |
|---|---|---|
| `ip m` | `maddress` | `monitor` |
| `ip s` | `sr` (segment routing) | `stats` |

Neither errors. They quietly do the wrong thing, which is worse. `ip a`, `ip l`, `ip r`, `ip n` are safe.

### Rule 1b — with no verb, `show` is implied

`ip addr`, `ip route`, `ip neigh`, `ip link` are all the `show` form. This is why the shortest useful
command in the suite is two characters (`ip a`), and it is worth knowing explicitly rather than absorbing
by imitation — it tells you that `ip <object>` alone is always safe to run, because the implied verb is
the read.

### The purest example in the toolset: `socat`

If Rule 1 feels like an abstraction, `socat` makes it concrete. It has **110 address types**, and nobody
memorises them, because they are generated from three slots:

```
  protocol          ×   family     ×   role
  TCP UDP UDPLITE       (nothing)      CONNECT LISTEN SENDTO
  SCTP DCCP UNIX        4              RECVFROM RECV DATAGRAM
  IP OPENSSL VSOCK      6              CLIENT
  EXEC PTY FILE …
```

So `TCP4-LISTEN`, `UDP6-SENDTO`, `UNIX-CONNECT`, `SCTP4-LISTEN` and `UDPLITE6-RECVFROM` are all names you
can *construct* — about thirty morphemes generating a hundred and ten names. `socat -hhh` prints the
whole list if you want to check yourself, and the `-h`/`-hh`/`-hhh` stacking is the same idiom as
`ip -s -s`.

This is what the rest of the page is claiming, in miniature: learn the slots, not the entries.

> ### ⚠️ Where Rule 1 breaks
>
> **`nft` and `kubectl` put the verb first**: `nft add table inet filter`, `kubectl get pods`. `ip`,
> `bridge`, `bpftool` and `docker` put the object first. There is no way to derive which ordering a tool
> chose — you have to know, or ask it. What you *can* derive, once you know the ordering, is every
> combination.
>
> **`bridge` and `tc` are not `ip` objects.** They are separate binaries with the same grammar and their
> own object sets — `bridge { link | fdb | mdb | mst | vlan | vni | monitor }`,
> `tc { qdisc | class | filter | chain | action }` — where a *qdisc* is a **queueing discipline**, the
> scheduler deciding the order and timing in which a device sends its queued packets. "Everything network
> is under `ip`" is nearly true, and the exceptions are `bridge`, `tc`, `ss` and `nft`.
>
> **`ip netns` is not netlink at all.** It is pure userspace: `ip netns add` makes a directory entry
> under `/run/netns` and bind-mounts `/proc/self/ns/net` onto it, so `ip netns list` is literally a
> directory listing. The kernel has no concept of a namespace *name*. That single fact explains why
> `ip netns list` cannot see Docker's namespaces — see [the state map](02-the-state-map.md).

---

## Rule 2 — `ip`'s verbs are the kernel's flags, and this is written down

Rule 1 tells you the shape. This tells you *why* the shape is what it is — and it is the strongest
"now you can guess it" lever on the page, because the kernel documents it in its own header.

**The objects come from netlink message names.** Netlink is the kernel's configuration API, and its
routing family names messages as verb-plus-object: `RTM_NEWLINK`, `RTM_DELADDR`, `RTM_GETROUTE`,
`RTM_NEWNEIGH`, `RTM_DELRULE`, and about twenty more suffixes. `ip link` / `ip addr` / `ip route` /
`ip neigh` / `ip rule` are those suffixes with a shell on them — and `tc qdisc`, `tc class`,
`tc filter` are the `RTM_*QDISC`, `*TCLASS`, `*TFILTER` families, which is why `tc` has `ip`'s shape
despite being a different binary.

**The verbs come from the modifier flags** — and here the mapping is exact, not inferred.
`include/uapi/linux/netlink.h` carries it as a comment in the kernel source:

```c
/* Modifiers to NEW request */
#define NLM_F_REPLACE 0x100  /* Override existing            */
#define NLM_F_EXCL    0x200  /* Do not touch, if it exists   */
#define NLM_F_CREATE  0x400  /* Create, if it does not exist */
#define NLM_F_APPEND  0x800  /* Add to end of list           */
```

and iproute2 implements precisely that:

| Verb | Netlink message | Flags |
|---|---|---|
| `add` | `RTM_NEW…` | `CREATE｜EXCL` — create, and fail if it exists |
| `change` | `RTM_NEW…` | `REPLACE` — modify, and fail if it does *not* exist |
| `replace` | `RTM_NEW…` | `CREATE｜REPLACE` — either way, end up with this |
| `append` | `RTM_NEW…` | `CREATE｜APPEND` — add at the end of the list |
| `del` | `RTM_DEL…` | — |
| `show` / `list` | `RTM_GET…` | `DUMP` — all of them |
| `get` | `RTM_GET…` | — one, resolved |

**This is the payoff.** You now know, without testing, why `ip addr add` fails on an address that is
already there and `ip addr replace` does not; why `change` fails on something that does not exist; and
why `append` exists at all for routes and not for links. Three verbs that looked like arbitrary synonyms
are three different flag combinations with different failure modes.

Two honest caveats. The **verb** half is quotable from the kernel header, so treat it as fact. The
**object** half is a strong correspondence rather than a documented design statement — and it is
imperfect: five `RTM_` families belong to `tc` rather than `ip`, a few are monitor-only with no verb at
all, and roughly half of `ip`'s objects (`netns`, `xfrm`, `l2tp`, `mptcp`, `macsec`, `fou`, `ila`, `sr`,
`ioam`, `tcp_metrics`) use generic netlink or plain userspace instead of rtnetlink.

**You can watch this happen**, which is better than believing it:

```bash
strace -e trace=network ss -tan 2>&1 | head
```

The trace names the kernel API you just invoked — `AF_NETLINK`, `SOCK_DIAG_BY_FAMILY`,
`NLM_F_REQUEST|NLM_F_DUMP`. Try it against `ip route show` and you get `NETLINK_ROUTE` and `RTM_GETROUTE`
instead. The abstraction becomes visible in one command.

---

## Rule 3 — Global options compose with every object

In `ip`, the options *before* the object are orthogonal to it: they modify output or scope, and they work
on anything. Verbatim from `man 8 ip`:

| Option | Long form | Meaning |
|---|---|---|
| `-4` / `-6` | `-family inet` / `inet6` | restrict to one address family |
| `-j` | `-json` | "Output results in JavaScript Object Notation (JSON)" |
| `-p` | `-pretty` | pretty-print — with `-j`, readable JSON without piping to `jq` |
| `-br` | `-brief` | "Print only basic information in a tabular format" |
| `-d` | `-details` | "Output more detailed information" |
| `-s` | `-stats`, `-statistics` | "Output more information" — **stackable**: `-s -s` gives more again |
| `-n` | `-netns` | "switches **ip** to the specified network namespace" — **takes an argument** |
| `-N` | `-Numeric` | print protocol/scope/dsfield numbers instead of names |
| `-a` | `-all` | "executes specified command over all objects" |
| `-c` | `-color` | colourise (`always`/`auto`/`never`) |
| `-b` | `-batch` | read commands from a file or stdin |
| `-t` | `-timestamp` | timestamp `monitor` output |

So `ip -j -d link show`, `ip -br addr`, `ip -6 -s route show` and `ip -n blue neigh` are all valid and all
derivable. Twelve options × twenty-seven objects × ten verbs is a great many commands from one table.

`-j` is the one worth building a habit around: JSON piped into `jq` turns "parse this text with `awk` and
hope the column order never changes" into a field lookup. It arrived in iproute2 4.14.1 (2017), so it is
present on anything current.

> ### ⚠️ Where Rule 3 breaks
>
> **`ss` has no `-j` at all.** `ss --json` is an unrecognised option. Its sibling in the *same package*
> supports JSON on every object and `ss` supports it nowhere — so "iproute2 speaks JSON" is a rule with
> one large, load-bearing hole in it. Parse `ss` output with `awk`, or read `/proc/net/tcp` yourself.
>
> **`tc` and `bridge` follow `ip`; `bridge` has no `-N`.** Close, not identical.

---

## Rule 4 — Conventions you can bet on, and the ones that will burn you

Across most of this toolchain, some letters mean the same thing:

| Flag | Usually means | Holds in |
|---|---|---|
| `-4` / `-6` | address family | `ip`, `ss`, `ping`, `curl`, `dig`, `nmap`, `iptables`, `socat` |
| `-v` | verbose | `curl`, `tcpdump`, `iptables`, most GNU tools |
| `-V` / `--version`, `-h` / `--help` | tell me about yourself | very nearly everything |
| `-j` / `--json` | machine-readable output | `ip`, `bridge`, `tc`, `nft`, `bpftool`, `kubectl -o json` |
| exit status `0` | success | everything — see the warning below |

**Now the traps.** These are not edge cases; they are the ones you will actually hit.

**1. `-n` has four meanings, and the flagship tool has the unexpected one.**

| Tool | `-n` means |
|---|---|
| `ss`, `tcpdump`, `nft`, `iptables`, `netstat`, `nmap` | numeric — don't resolve names |
| **`ip`, `tc`, `bridge`** | **`--netns`** — and it takes an argument |
| `conntrack` | `--src-nat`, which also takes an argument |
| `kubectl` | `--namespace` |

Worse, `ip` and `ss` — same package — **swap `-n` and `-N`**: in `ip`, `-N` is numeric and `-n` is netns;
in `ss`, `-n` is numeric and `-N` is netns. And because `ip -n` swallows the next token whatever it is,
the failure is genuinely disorienting:

```
$ ip -n link show
Cannot open network namespace "link": No such file or directory
```

There is no namespace called `link`. You asked for one anyway. `nsenter -n` meaning *the net namespace*
is a third data point that `-n` is not reliably "numeric" — treat the letter as ambiguous and check.

**2. `-s` means five different things.** `ip`/`tc`/`bridge` statistics · `ss` a summary that skips the
socket list · `tcpdump` **snaplen**, and it takes a byte count · `nft` stateless · `ping` **payload
size** · `ethtool` `--change`, which is a *write*. And `nmap`'s `-sS`/`-sT` are not `-s` at all; the
letter after it is part of the scan-type name.

**3. `-d` means four different things.** `ip`/`tc`/`bridge` details · `tcpdump` dump the compiled BPF ·
`nft` debug level · `ss` DCCP sockets · `conntrack` `--dst`. In a great many other tools it is debug or
delete.

**4. `dig` is not a flag-based tool.** Its syntax is `dig @server name type`: the server is positional
with an `@` sigil, the name and type are positional in any order, and its behaviour toggles are
`+option` — negated by prefixing `no` (`+nocomments`) or assigned with `=` (`+timeout=2`). Nothing you
know about `-` flags transfers. It has no `-n`.

**5. `conntrack` inverts the whole convention** and should be treated as a do-not-guess tool: its
**verbs are single capitals** (`-L` list, `-E` events, `-D` delete, `-F` flush, `-C` count, `-S` stats)
and the lowercase letters are tuple fields (`-s` src, `-d` dst, `-p` proto). Its `-j` means "any NAT",
not JSON.

**6. `ethtool` is a rule with two exceptions, exactly where you would bet wrong.** Lowercase shows,
uppercase sets — `-g`/`-G` ring sizes, `-k`/`-K` offloads, `-c`/`-C` coalescing, `-l`/`-L` channels. Then
**`-s` is `--change` (a write) and `-S` is `--statistics` (a read)**: inverted. Learn the rule, then learn
that one pair.

**7. `tcpdump` has no `-4`/`-6`.** Address family goes in the filter expression (`ip`, `ip6`), not in a
flag. And `-s 0` — in every tutorial ever written — has been unnecessary since tcpdump 4.0: the default
snaplen is already 262144 bytes.

> ### ⚠️ Exit codes do not generalise, at all
>
> `man 8 ip` says it returns 0 for success, 1 for a syntax error and 2 for a kernel error. Measured, it
> returns **1** for a missing device, **2** for a duplicate, and **255** for a bad verb *or* for `help`.
> `ethtool` returns **75** for a missing device. `dig` returns **9** when it cannot reach a server.
>
> **Only `0 = success` is portable.** Never branch on a guessed non-zero code.

## Rule 5 — What the names expand to (and which expansions are folklore)

Knowing the expansion fixes the spelling and, more often, tells you what the tool is *for*. But this is
also where the internet is least reliable, so the tables below are split by whether a primary source
actually says it. Assume nothing in the third table.

### Confirmed by the project, the man page, or the commit that introduced it

| Name | Expands to | Where it is written down |
|---|---|---|
| `lsof` | list open files | `man 8 lsof` NAME line |
| `tc` | traffic control | `man 8 tc` NAME line |
| `nc` | netcat | `man 1 nc` |
| `socat` | SOcket CAT | `man 1 socat` NAME line |
| `curl` | "a play on *Client for URLs*" | curl's own FAQ, which also allows *Client URL Request Library* |
| `conntrack` | connection tracking | `man 8 conntrack`: "command line interface for netfilter connection tracking" |
| `nft` | the nftables CLI — netfilter tables | the nftables project |
| `veth` | **Virtual ETHernet** | the kernel commit that added it says so in words: *"Veth stands for Virtual ETHernet. It is a simple tunnel driver that works at the link layer and looks like a pair of ethernet devices interconnected with each other."* |
| `macvlan` | MAC-VLAN | the driver's own Kconfig prompt is literally `MAC-VLAN support` |
| `unshare` | "disassociate parts of the process execution context" | `man 2 unshare` NAME line — the clearest self-describing name in the toolchain, and see below |
| `UTS` (namespace) | UNIX Time-sharing System, via `struct utsname` | the kernel header comment `/* New utsname namespace */`, and Michael Kerrisk in LWN 531114 |
| `BPF` | **BSD** Packet Filter, in the 1992 paper that introduced it | McCanne and Jacobson, *"The BSD Packet Filter"*, LBL, Dec 1992 |

Two of those are worth more than a table row.

**`unshare` is the inverse of `clone`.** Both syscalls take the *same* `CLONE_NEW*` flags, and the name
tells you which way round the subject is: `clone(CLONE_NEWNET)` means "the new child gets a new network
namespace"; `unshare(CLONE_NEWNET)` means "*I* stop sharing the one I already have." Once you see that,
`unshare` and `nsenter` and `ip netns` stop being three unrelated tools and become three positions on one
mechanism — make a new one, enter an existing one, name one so it persists.

**`BPF` is the cautionary tale about expansions.** The original paper says *BSD* Packet Filter; today
kernel.org glosses it *Berkeley* Packet Filter (the authors were at Lawrence **Berkeley** Laboratory,
which is presumably how it drifted); and the eBPF Foundation's position is that *"eBPF is now considered
a standalone term that doesn't stand for anything."* Three defensible answers, depending on which decade
you are standing in.

### Named after a person or a joke, not a function

| Name | Story |
|---|---|
| `ping` | Mike Muuss named it after sonar. *"Packet InterNet Groper"* is a later backronym |
| `mtr` | widely reported as "Matt's traceroute", after Matt Kimball — plausible, and not stated by the project's own docs |

### Popular expansions that no primary source confirms

Use these as memory aids. Do not repeat them as facts.

| Name | The popular expansion | What the documentation actually says |
|---|---|---|
| `ss` | "socket statistics" | `man 8 ss` NAME reads **"ss - another utility to investigate sockets"**. No expansion anywhere |
| `dig` | "domain information groper" | BIND's own manual calls it "a flexible tool for interrogating DNS name servers" and never expands the name |
| `ethtool` | "ethernet tool" | `man 8 ethtool` NAME is a description: "query or control network driver and hardware settings". Near-certainly the intended reading; nobody wrote it down |
| `nsenter` | "namespace enter" | NAME is "run program in different namespaces"; the source file self-describes as *"command-line interface for `setns(2)`"*. A transparent compound, still undocumented |
| `bpftool` | "BPF tool" | NAME is "tool for inspection and simple manipulation of eBPF programs and maps" |
| `ipvlan` | "IP VLAN" | the nearest primary gloss is `man 8 ip-link`: "Interface for L3 (IPv6/IPv4) based VLANs" |
| `devlink` | "device link" | the networking `devlink` has no documented expansion — and there is an **unrelated** `struct device_link` in the Linux driver core that genuinely does mean *device link*, which is the likely source of the gloss |
| `pgrep` | "process grep" | NAME is "look up, signal, or wait for processes based on name and other attributes" |

### The kernel corrects its own names, but only where it can

Two examples worth knowing, because they explain naming inconsistencies you will otherwise trip over.

**`CLONE_NEWNS` versus `/proc/<pid>/ns/mnt`.** Mount namespaces came first, in 2002, and got the generic
flag name `CLONE_NEWNS` — "new namespace" — because nobody expected there to be other kinds. Every
namespace added afterwards got a specific suffix: `NEWNET`, `NEWPID`, `NEWUTS`, `NEWIPC`, `NEWUSER`,
`NEWCGROUP`, `NEWTIME`. The ABI flag name is frozen forever, but when `/proc/<pid>/ns/` was added in
Linux 3.8 it was a fresh surface, so it got the accurate name: the file is **`mnt`**, not `ns`. So the
odd one out in the flag list is a 2002 artefact, and the filesystem quietly fixed it.

**`ip_conntrack` became `nf_conntrack`.** The original module was IPv4-only, so it was `ip_`-prefixed. When
it was generalised to handle IPv6 too, the prefix changed to **`nf_`** for *netfilter* — which is why the
sysctls you actually use today are `net.netfilter.nf_conntrack_max` and not `net.ipv4.*`. The prefix is
telling you the layer it belongs to, and the rename is telling you it stopped being IPv4's business.

### Even primary sources disagree — one worked example

`ip-link(8)` glosses the VXLAN device type as *"vxlan - Virtual eXtended LAN"*. RFC 7348, which defines
the protocol, calls it *Virtual eXtensible Local Area Network*. iproute2's own man page teaches an
expansion the standard does not use.

So the rule for this whole page: **an expansion is a memory aid, and the tool's behaviour is the fact.**
When the two seem to conflict, trust `<tool> help`.

## Rule 6 — Filter languages are separate grammars, and they do not match

It is tempting to assume the capture filter you learned for `tcpdump` works in `ss`. It does not.

**`tcpdump` uses libpcap's expression language**, which is genuinely compositional —
`[direction] [protocol] [type] value`, joined by `and` / `or` / `not`:

```
src host 10.0.0.5          # direction + type + value
tcp port 443               # protocol + type + value
not arp and dst net 10/8
tcp[tcpflags] & tcp-syn != 0     # byte-offset form: SYN set
```

Learn the four slots and you can write filters you were never shown. The byte-offset form is the escape
hatch for anything the named primitives don't cover.

**`ss` has its own filter language, with a different backend.** It reads similarly — TCP state names,
`dport`/`sport` comparisons, `and` / `or` / `not` — but it compiles to *inet_diag bytecode* evaluated
inside the kernel's socket-diagnostics layer, not to a BPF program. `man 8 ss` never mentions libpcap.
Its grammar is also stricter than it looks:

```
ss -tan state established              # OK
ss -tan sport = :22                    # OK
ss -tan dport lt 1024                  # OK
ss -tan '( sport = :22 or dport = :22 )'   # OK
ss -tan not state established          # REJECTED — `state` is a separate production
```

`state` sits outside the boolean expression, so you cannot negate it inline. Use the named macros
instead, which `ss --help` defines for you: `connected`, `synchronized`, `bucket`, `big`, `all`. Do not
carry a `tcpdump` filter across; write it in `ss`'s own terms.

The transferable lesson is the meta-rule: **when a tool has a filter language, find its four or five
slots.** Almost every one of them is "which direction, which protocol, which field, which value", and
once you have located those slots you can generate expressions instead of recalling them.

---

## Rule 7 — The same trick works on the kernel's own files

Commands are not the only guessable thing. Two rules cover most of the `/proc` and `/sys` paths you will
ever need, and they belong here rather than buried in a map, because they are grammar:

**Sysctl keys are `/proc/sys` paths with the dots turned into slashes.**

```
net.ipv4.ip_forward              ->  /proc/sys/net/ipv4/ip_forward
net.netfilter.nf_conntrack_max   ->  /proc/sys/net/netfilter/nf_conntrack_max
```

It runs both ways: if you can `cat` it you can `sysctl` it, which makes `sysctl -a | grep <word>` a search
over every tunable on the machine.

**`/sys/class/net/<dev>/` is one file per field.** So "where does the kernel keep this interface's MTU" is
not a lookup, it is a construction: `/sys/class/net/eth0/mtu`. Likewise `address`, `operstate`, `carrier`,
`mtu`, `statistics/rx_packets`.

Both rules have a hard edge, and the edge is the interesting part — the *path* is derivable and the
*semantics* are not. `/proc/sys/net/ipv4/conf/` has an `all`, a `default` and one directory per device,
and how they combine is defined **per parameter**: `rp_filter` takes the maximum of `all` and the device,
`log_martians` ORs them, `accept_redirects` ANDs them when forwarding is on and ORs them when it is off,
and `forwarding` broadcasts a write to every interface. Four parameters, four rules, no pattern.

**[The state map](02-the-state-map.md)** is where those rules are worked out in full, along with the
territory they apply to.

---

## Rule 8 — Derive it, don't recall it

The fastest answer is almost never a search engine. But the ranking below is not the one most guides
give, because **the lab container has no man pages at all** — `/usr/share/man` is empty in `netshoot`,
and `man`, `man -k` and `apropos` are simply unavailable. That inverts the usual advice for container
work: `--help` is not the fallback, it is the baseline.

| Move | Answers | Works offline in `netshoot`/`netlab`? |
|---|---|---|
| `<tool> --help 2>&1 \| grep -i <word>` | "which flag was it?" | ✅ always |
| `ip <object> help 2>&1 \| grep -i <word>` | every verb and argument for that object | ✅ always — note the redirect |
| `nft describe <expression>` | the datatype and every symbolic constant, e.g. all the TCP flag names | ✅ |
| `tc qdisc add <KIND> help` | that qdisc's options — `tc` documents itself recursively | ✅ |
| `iptables-translate <old rule>` | the nftables equivalent of a rule you already know | ✅ |
| `sysctl -a \| grep <word>`, or `find /proc/sys/net -name '*<word>*'` | the exact tunable name | ✅ |
| `strace -e trace=network <cmd>` | the kernel API name behind any CLI call | ✅ |
| `<TAB><TAB>` after a tool name | the legal object list | ⚠️ needs `bash-completion`, absent in netshoot |
| `man <tool>`, `man -k <topic>`, and the section numbers (1 commands, 5 file formats, 7 overviews, 8 admin) | the whole contract | ❌ **not installed in the lab image** |
| `kubectl explain <resource>.<field>`, `kubectl api-resources` | the API schema, live from the server | needs an API server |
| `tldr`, `cheat.sh`, `explainshell.com` | worked examples | ❌ network or install required |

> ### ⚠️ The trap that costs the most time: `ip <object> help` writes to **stderr** and exits **255**
>
> ```bash
> ip link help | grep vlan          # prints NOTHING. The help went to stderr.
> ip link help 2>&1 | grep vlan     # works
> ```
>
> The exit code is 255 too, so `ip link help && echo ok` never prints `ok`. Its sibling `tc qdisc help`
> writes to stdout and exits 0, and `ss --help` and `nft --help` both behave normally. Same package,
> three behaviours. **Always `2>&1 |` when grepping `ip` help.**

The two to build reflexes around are **`ip <object> help`** and **`kubectl explain`** — both are the tool
describing itself, which means they cannot go stale the way a cheat sheet can.

---

## How to practise this, and what the evidence says about it

[Derive it](06-derive-it.md) exists because reading a grammar is not learning it. Producing an item you
were never shown is called *generation*, and it beats re-reading by a wide and well-replicated margin
(d ≈ 0.40 across 445 effect sizes). But the research is specific about what makes it work, and two of the
conditions are easy to get wrong:

- **Feedback has to re-derive the answer, not just state it.** Elaborated feedback transfers (d ≈ 0.70);
  bare correct-answer feedback did nothing for transfer in any analysis and ran slightly *negative* for
  inference questions. This is why every reveal on that page explains which rule produced the answer
  rather than just printing the command.
- **Success matters more than struggle.** Transfer improves sharply with high initial success rates,
  which cuts against the folk version of "make it hard". If a drill is failing you every time, the
  missing rule is the problem, not your effort.

And the honest limit: there is good evidence that a consistent grammar is *learnable*, and no direct
evidence that learners reliably *generate* untaught commands from one. That is this page's bet, not a
proven result.

---

## Where these rules stop

They generate *plausible* commands, which is the point — but plausible is not correct, and the difference
matters when the command writes state rather than reading it.

- A derived read (`ip -j -d neigh show`) is safe: worst case it errors.
- A derived write (`ip route replace …`, `nft flush ruleset`) can take a machine off the network. Derive
  it, then confirm it against `help` before you run it, and prefer the read that shows you the current
  value first.
- Nothing here tells you *whether you should* run something. That judgement is what the acts are for, and
  [the debugging method](../networking-fundamentals/act-5-kubernetes/08-debugging.md) is the page to
  reread when the question is "which of these five things do I check first".

---

Next: **[the state map](02-the-state-map.md)** — the same trick applied to the kernel's own files. Or go
straight to **[by question](04-by-question.md)** if you arrived with a symptom.
