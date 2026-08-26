# The Instrument Panel

**This directory is deliberately not teaching.**

Everything in [`networking-fundamentals/`](../networking-fundamentals/README.md) follows one rule:
never hand you an answer to a question you don't yet have. This directory breaks that rule on purpose,
for the same reason [`exam-prep/`](../exam-prep/README.md) does — it serves a different moment. The acts
are for the first time you meet an idea. This is for the four-hundredth: you already understand
conntrack, you are on a call, and you need to remember which file the kernel keeps it in.

A reference is a map. It tells you what is in the territory so you don't have to go and check, and that
is a different job from walking the territory, which is what the acts are for. So the pages here
describe; they don't teach, persuade, or motivate. Where you want any of those, they link back into
the lessons.

## What you need before this is useful

**Acts I–IV.** These pages assume `/proc/net/tcp`, namespaces, veth pairs, `iptables` and `conntrack` are
already yours — they are a reference for material you have met, not an alternative to meeting it. Some
pages reach further: [by question](04-by-question.md) and [derive it](06-derive-it.md) have sections on
Kubernetes and on eBPF datapaths that assume Acts V–VI, and those sections say so where they start.

## The one thing to read even if you never look anything up

**Start with the interface a tool speaks.** Everything else here is finite, and none of it will contain
the flag you need at 3am; the interface is the part that scales.

Every tool in this reference is a client of one of **eight kernel interfaces**, each defined by a
syscall you can see in `strace` — so the classification is measurable rather than a matter of opinion:

[`netlink`](tools/netlink/README.md) · [`procfs`](tools/procfs/README.md) ·
[`socket`](tools/socket/README.md) · [`packet`](tools/packet/README.md) ·
[`probe`](tools/probe/README.md) · [`nsapi`](tools/nsapi/README.md) ·
[`httpapi`](tools/httpapi/README.md) · [`local`](tools/local/README.md)

That one fact reorganises everything. Tools sharing an interface **share a grammar, share a blind spot,
and are often substitutable**; tools on different interfaces never substitute, however alike their
output looks. It is also where the derivation lives: `netlink` explains why `ip addr add` fails on an
existing address and `ip addr replace` does not — three verbs that look like synonyms are three
netlink flag combinations with three different failure modes — and `procfs` explains how to construct
a `/proc` or `/sys` path nobody showed you.

Then go to **the tool itself**. Each of the seventy-two has a page carrying its whole capability
surface, the commands this course runs through it, and what its interface can never tell you:
[`ip`](tools/netlink/ip.md) · [`ss`](tools/netlink/ss.md) · [`tcpdump`](tools/packet/tcpdump.md) ·
[`kubectl`](tools/httpapi/kubectl.md) · [`openssl`](tools/socket/openssl.md), and
[sixty-seven more](tools/README.md).

If you arrived with a broken machine rather than a question about a tool, skip all of that and go to
**[by question](04-by-question.md)** — a real failure arrives as a symptom, not as a tool name.

| Page | Answers |
|---|---|
| **[The eight interfaces](tools/README.md#the-eight-interfaces--the-whole-roster-on-one-screen)** | Which kernel API a tool speaks — and therefore what it can possibly know, how its syntax is shaped, and what no flag will ever make it tell you. **Read this first**, then the page for the interface you landed on |
| **[The roster](tools/README.md)** | One row per tool, for when you want the whole thing on a screen rather than one tool in depth. It is also the front door of the directory below it: each interface is a subdirectory led by its own page, and each tool is a page inside one, carrying its whole capability surface and the commands this course runs through it |
| **[What to reach for instead](tools/README.md#six-to-stop-reaching-for-and-two-to-start)** | Which six tools are here only because other people's runbooks are full of them, which two are new enough to install deliberately, and — for each — what the swap actually costs |
| **[By question](04-by-question.md)** | You have a symptom, not a tool name. **The one to read when something is broken** |
| **[Conventions and names](01-the-grammar.md)** | The claims that hold across the *whole* toolchain: which flag letters mean the same thing everywhere, which name expansions are folklore, and why the filter languages do not match |
| **[Lab and shell commands](05-per-act-commands.md)** | The non-networking commands the lessons run — `ls`, `grep`, `exec`, `cc` — taken apart |
| **[Derive it](06-derive-it.md)** | Drills that make you *write* commands you were never shown |

## What this is not

**Not the exam cheat sheet.** [`exam-prep/kubectl-speed.md`](../exam-prep/kubectl-speed.md) is that, and
is honest about being drills against a clock; this directory is about Linux and the kernel's own
interfaces, and does not repeat what lives there. **Not a progress tracker.**
[`Toolbelt.md`](../Toolbelt.md) answers *"what should I be fluent in by now?"* — a question about the
journey, in the journey's order. These pages are sorted for lookup and say nothing about what you should
have earned yet.

## How this directory is held honest

The claims on these pages are checked rather than trusted, by `tools/check_pedagogy.py`. Every facet
vocabulary is closed, so a value invented in one row is a warning. Every summary table must name exactly
the rows it summarises, in **both** directions — which is what makes the interface taxonomy hold, because
a tool cannot be added to the roster without being placed, and being unplaceable is how every tool
taxonomy eventually dies. A `superseded` verdict must name a successor that is itself on the roster, since
"deprecated" with no replacement is a complaint rather than advice. And every sentence that quotes
in-image *output* — the most convincing kind, and the first to go stale — declares itself in
`capabilities.json`, so `tools/probe-lab.py` can re-run the command against `netlab:latest` and turn the
page red instead of leaving it confidently wrong.

Each check argues its own case in its docstring, which is where the argument belongs: next to the code, so
it cannot drift out of step with what the code actually does. Two things it cannot check for itself get an
agent instead — `technical-accuracy-checker` runs the *lesson* command blocks in the lab image, and each
`roster only` marker is verified by grep against the lesson sources before it ships.

One check exists only to protect the others, and it is a *hard* failure rather than a warning:
`check_reference_shape` asserts that the roster and all eight interface pages are where the checks above
expect them. This directory has been restructured twice; the second time, the guards went quiet rather
than red, because every one of them reads a file by path — and a checker whose path has gone stale does
not complain, it passes.
