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
| **[Filter languages](#filter-languages-are-separate-grammars-and-they-do-not-match)** | why `tcpdump`, `ss` and `tshark` expressions are three languages, not one |

**Where to go instead.** To derive a command you were never shown, start at
[the map](03-the-map.md) for which station it acts on, then the interface it speaks —
[the eight of them](tools/README.md#the-eight-interfaces--the-whole-roster-on-one-screen) — then the
tool's own page.

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

Next: **[the map](03-the-map.md)** — the ten kernel checkpoints a packet crosses, and which tool reads
each one. Or go straight to **[by question](04-by-question.md)** if you arrived with a symptom.

