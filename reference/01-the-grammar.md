# Conventions and names — what holds across the whole toolchain

**This page is what is left when the derivable parts move to where they are derivable from.**

Most of what used to be here was *per interface*, not per toolchain: `TOOL OBJECT VERB` and the
netlink flag semantics that make `add`, `change` and `replace` three different failure modes are facts
about [`netlink`](tools/netlink/README.md), shared by its thirteen tools. The trick of reading the
kernel's own files is a fact about [`procfs`](tools/procfs/README.md), shared by its fourteen. Those
pages now carry them, once each, next to the tools they apply to.

What remains here is the material that is genuinely *about the whole toolchain* and loses its point
when scattered across seventy-two pages:

| | Answers |
|---|---|
| **[Conventions](#conventions-you-can-bet-on-and-the-ones-that-will-burn-you)** | which flag letters mean the same thing everywhere — and which look like they do and do not |
| **[Names](#what-the-names-expand-to-and-which-expansions-are-folklore)** | what the abbreviations expand to, and which popular expansions no primary source confirms |
| **[Filter languages](#filter-languages-are-separate-grammars-and-they-do-not-match)** | why `tcpdump`, `ss` and `tshark` expressions are three languages, not one |

**Where to go instead.** To derive a command you were never shown, start at the interface it speaks —
[the eight of them](tools/README.md#the-eight-interfaces--the-whole-roster-on-one-screen) — then the
tool's own page. To *practise* deriving, [derive it](06-derive-it.md) is the drills.

---
## Conventions you can bet on, and the ones that will burn you

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
> `ip(8)` documents 0 for success, 1 for a syntax error and 2 for a kernel error. Measured, it
> returns **1** for a missing device, **2** for a duplicate, and **255** for a bad verb *or* for `help`.
> `ethtool` returns **75** for a missing device. `dig` returns **9** when it cannot reach a server.
>
> Check it rather than trusting either of us — three lines, and the lab needs no man pages for them:
>
> ```bash
> ip link show nosuchdev; echo $?        # 1
> ip addr add 127.0.0.1/8 dev lo; echo $?  # 2 — already there
> ip link nosuchverb; echo $?           # 255
> ```
>
> **Only `0 = success` is portable.** Never branch on a guessed non-zero code.

## What the names expand to (and which expansions are folklore)

Knowing the expansion fixes the spelling and, more often, tells you what the tool is *for*. But this is
also where the internet is least reliable, so the tables below are split by whether a primary source
actually says it. Assume nothing in the third table.

The citations use the `tool(section)` form because **the lab image ships no man pages** — `man` is not
installed and `/usr/share/man` is empty. Read them at [man7.org](https://man7.org/linux/man-pages/) or
`manpages.debian.org`, or get the same facts in-image from `<tool> help` and `<tool> --help`.

### Confirmed by the project, the man page, or the commit that introduced it

| Name | Expands to | Where it is written down |
|---|---|---|
| `lsof` | list open files | `lsof(8)` NAME line |
| `tc` | traffic control | `tc(8)` NAME line |
| `nc` | netcat | `nc(1)` |
| `socat` | SOcket CAT | `socat(1)` NAME line |
| `curl` | "a play on *Client for URLs*" | curl's own FAQ, which also allows *Client URL Request Library* |
| `conntrack` | connection tracking | `conntrack(8)`: "command line interface for netfilter connection tracking" |
| `nft` | the nftables CLI — netfilter tables | the nftables project |
| `veth` | **Virtual ETHernet** | the kernel commit that added it says so in words: *"Veth stands for Virtual ETHernet. It is a simple tunnel driver that works at the link layer and looks like a pair of ethernet devices interconnected with each other."* |
| `macvlan` | MAC-VLAN | the driver's own Kconfig prompt is literally `MAC-VLAN support` |
| `unshare` | "disassociate parts of the process execution context" | `unshare(2)` NAME line — the clearest self-describing name in the toolchain, and see below |
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
| `ss` | "socket statistics" | `ss(8)` NAME reads **"ss - another utility to investigate sockets"**. No expansion anywhere |
| `dig` | "domain information groper" | BIND's own manual calls it "a flexible tool for interrogating DNS name servers" and never expands the name |
| `ethtool` | "ethernet tool" | `ethtool(8)` NAME is a description: "query or control network driver and hardware settings". Near-certainly the intended reading; nobody wrote it down |
| `nsenter` | "namespace enter" | NAME is "run program in different namespaces"; the source file self-describes as *"command-line interface for `setns(2)`"*. A transparent compound, still undocumented |
| `bpftool` | "BPF tool" | NAME is "tool for inspection and simple manipulation of eBPF programs and maps" |
| `ipvlan` | "IP VLAN" | the nearest primary gloss is `ip-link(8)`: "Interface for L3 (IPv6/IPv4) based VLANs" |
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

## Filter languages are separate grammars, and they do not match

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
inside the kernel's socket-diagnostics layer, not to a BPF program. `ss --help | grep -i bpf` returns
exactly one line — `-b, --bpf  show bpf filter socket information` — and that flag prints a filter some
*other* process attached to a socket. Nothing in `ss` compiles your filter to BPF, and libpcap appears
nowhere. Its grammar is also stricter than it looks:

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

## How to practise this, and the honest limit

Reading a grammar is not learning it. [Derive it](06-derive-it.md) is the other half: every drill there
withholds the command and makes you build it from the rules above, and it carries what the evidence does
and does not support about working that way.

The limit is worth stating here rather than there. There is good evidence that a consistent grammar is
*learnable*, and no direct evidence that learners reliably *generate* untaught commands from one. That is
this page's bet, not a proven result.

---

## Where these conventions stop

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

Next: **[`procfs`](tools/procfs/README.md)** — the same trick applied to the kernel's own files. Or go
straight to **[by question](04-by-question.md)** if you arrived with a symptom.

