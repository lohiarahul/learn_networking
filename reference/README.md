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

Start with **[the grammar](01-the-grammar.md)**.

Every other page here is finite, and none of them will contain the flag you need at 3am. The grammar page
is the one that scales, because the tools were not named at random: `ip` has a closed object list and one
verb set that repeats across all of it, those verbs turn out to *be* the kernel's own netlink flags, and
the same trick reaches into `/proc` and `/sys`. Learn those shapes and you can work out commands and paths
nobody taught you — which is the only skill here that survives a tool changing its flags.

Then read **[by question](04-by-question.md)**, which is the page you will actually reach for under
pressure, because a real failure arrives as a symptom and not as a tool name.

| Page | Answers |
|---|---|
| **[The grammar](01-the-grammar.md)** | Why the commands are spelled the way they are, and how to work out one you were never shown |
| **[The state map](02-the-state-map.md)** | Where the kernel keeps a fact, and how to construct a `/proc` or `/sys` path |
| **[The index](03-the-index.md)** | One row per tool: what its name expands to, and the one thing only it can show you |
| **[By question](04-by-question.md)** | You have a symptom, not a tool name. **The one to read second** |
| **[Command reference, by act](05-per-act-commands.md)** | Every command Acts I–IV run, broken down element by element |
| **[Derive it](06-derive-it.md)** | Drills that make you *write* commands you were never shown |

The numbering is the reading order for someone going through once; the sidebar order is the same. If you
came here with a broken machine, skip to [by question](04-by-question.md) and come back.

## What this is not

- **Not a cheat sheet for the exam.** [`exam-prep/kubectl-speed.md`](../exam-prep/kubectl-speed.md)
  is that, and it is honest about being drills against a clock. This directory is about Linux and the
  kernel's own interfaces, and it does not repeat what lives there.
- **Not a progress tracker.** [`Toolbelt.md`](../Toolbelt.md) answers *"what should I be fluent in by
  now?"* — a question about the journey, in the order the journey introduces things. This directory is
  sorted for lookup, not for learning, and says nothing about what you should have earned yet.
- **Not a claim of coverage.** Several tools in this index are named by the roster and used by no
  lesson. Every row says which it is. A reference that lets you assume the course taught something it
  didn't is worse than one with gaps.

## How this directory is held honest

`tools/check_pedagogy.py` skips this directory for the Predict-first and ladder invariants, for the same
reason it skips `exam-prep/` — see `is_lesson()` there. A lookup table with a "Predict first" block
would be incoherent.

Link integrity still applies, and it does real work here: every "taught in" citation on
[the index](03-the-index.md) is a relative link, so a lesson that gets renamed or deleted breaks the
build rather than quietly leaving a lie in a table.

The two claims this directory can't check for itself are accuracy and honesty, so both get an agent:
`technical-accuracy-checker` runs every command block in the lab image, and each `roster only` marker is
verified by grep against the lesson sources before it ships.
