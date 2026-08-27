#!/usr/bin/env python3
"""gen-tool-pages.py — one page per tool, in `reference/tools/`.

Why this exists
---------------
The reference used to be sorted by *kind of knowledge*: grammar on one page, `/proc` paths on
another, an index of tools on a third, the commands each lesson runs on a fourth. Answering
"what can `ip` do and how do I drive it" meant visiting four pages and assembling the answer.
The tool is the thing a reader holds in their head, so the tool is the primary key here.

Unlike `gen-command-tables.py`, this generator *owns* its output files completely. That is only
safe because it has no hand-written half: everything worth writing lives in
`reference/capabilities.json`, which is edited by hand, and in `reference/tools/README.md`, whose
`Speaks` column is guarded by `check_index_facets`. Never hand-edit a *tool* page — the next run
overwrites it. Edit the JSON.

Not every row gets a page, and the roster decides which do. A row whose **Tool** cell is a link claims
a page; a row whose Tool cell is a bare code span is a row and nothing more, and this generator deletes
any page it finds for one. That exists because a page-per-tool is right for the tools a lesson actually
runs and dishonest for a tool with no route through the course at all: `devlink` is not even installed
in the lab image, and a facet table plus a "4 commands, grouped by what you are trying to find out"
preamble is more furniture than content. The roster row already carries the sentence that matters — the
one thing only that tool shows you — so the row *is* the entry, and any command on it worth keeping
moves to `reference/04-by-question.md`, where a reader arrives holding a symptom rather than a name.

Each page is assembled from what the JSON says about the tool: what its name expands to, what it can
do to the world, its standing, the handful of flags that carry their weight, its capability surface,
and how this course drives it — in roughly the order the questions arrive in.

The roster is down to four columns because a table nobody can read on one screen is not an index, so
the two facts that used to be columns there — the name expansion and the `read-only`/`mutate`/`live`
mode — are fields in the JSON now, rendered as rows of the facet table below each page's title. That
is also better provenance: they are per-tool data, and they now live with the rest of the per-tool
data instead of being parsed back out of a rendered table.

The two hand-written files inside `reference/tools/` are the `README.md`s: the roster at the top,
and one per interface directory. Those are inputs, not output, and the orphan sweep at the bottom
of `main()` knows to leave them alone.

What is shared rather than repeated
----------------------------------
A tool page says nothing about the grammar shape it shares with its twelve siblings, because
that belongs to the interface, not the tool: the netlink flag table would otherwise be duplicated
thirteen times and the `/proc` path rules fourteen. Those live in each interface directory's own
`README.md` — `reference/tools/netlink/README.md` is both the netlink page and the landing page
for the thirteen tools under it — and every tool page's `Speaks` row links to its own.

The same logic retired two sections these pages used to carry. The interface's blind spot was
printed in full on all seventy-two of them and is now one row of the facet table, and the list of
same-interface siblings was seventy-two copies of a list the directory README and the sidebar both
already give you.

Usage
-----
    python3 tools/gen-tool-pages.py           # write the pages
    python3 tools/gen-tool-pages.py --check   # exit 1 if any page is stale (for CI)
"""
from __future__ import annotations
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "reference", "tools", "README.md")
DATA = os.path.join(REPO, "reference", "capabilities.json")
LAB = os.path.join(REPO, "reference", "lab-inventory.json")
OUT = os.path.join(REPO, "reference", "tools")

# The interface a tool speaks decides which shared page explains its grammar, and what it can never
# know. Written out per interface rather than fitted to one template, because the sentence a reader
# needs is not the same shape in all eight cases — `probe`'s blind spot is that it has none, and
# "cannot tell you nothing" is not a sentence. Kept in step with `INTERFACES` in check_pedagogy.py
# and the summary table on the roster.
IFACE_BLIND = {
    "netlink": "cannot tell you what a packet *did*. It reports configured and tracked state, never "
               "a packet's path — a property of the [interface](README.md), not of this tool",
    "procfs": "cannot tell you anything the kernel does not already export as a file, and it reads a "
              "*snapshot*, so a transient is invisible — a property of the "
              "[interface](README.md), not of this tool",
    "socket": "cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs "
              "another [interface](README.md)",
    "packet": "cannot tell you which process or rule was responsible. It sees bytes on a link, not "
              "the host state behind them — a property of the [interface](README.md), not of this tool",
    "probe": "has none worth the name — this is the only [interface](README.md) that can say which "
             "kernel function dropped your packet. It does need a running target",
    "nsapi": "cannot tell you what is *inside* a namespace. These move you between namespaces; they "
             "read nothing — a property of the [interface](README.md), not of this tool",
    "httpapi": "cannot tell you what the kernel actually did. Every one of these reports *intent*, "
               "and Acts V–X exist because intent and mechanism diverge",
    "local": "cannot tell you anything at all about your machine. These reshape input another tool "
             "produced — a property of the [interface](README.md), not of this tool",
}

# When a name is not its own implementation. Measured by tools/probe-lab.py via `readlink -f`,
# so a rebuilt image that swaps a provider changes these pages rather than quietly making them wrong.
PROVIDER_NOTE = {
    "busybox": "provided by **BusyBox**, which implements a *subset* of the flags below "
               "(`{tool} --help` is the authority on which)",
    "xtables-nft-multi": "provided by **`xtables-nft-multi`**, the nftables-backed multi-call "
                         "binary (which is the `Standing` row below, measured rather "
                         "than argued)",
}

MARK_NOTE = {
    "†": "**Two interfaces, depending on the build.** `netlink` on the nf_tables backend, "
         "`setsockopt` on legacy — and **`iptables -V` tells you which**. Measured: "
         "`iptables -t nat -L` opens `NETLINK_NETFILTER`, so on a current box this is an nftables "
         "front end.",
    "‡": "**Two interfaces, depending on the flag.** `packet` for `-sS`, the half-open scan; "
         "`socket` for the `-sT` default, which is an ordinary `connect()` your application logs.",
    "§": "**Not what people assume.** It opens `AF_INET, SOCK_DGRAM` — ICMP datagram sockets, not "
         "`SOCK_RAW`. Gated by `net.ipv4.ping_group_range`, which is why `ping` no longer needs to "
         "be setuid.",
    "¶": "**Files first.** Measured against `localhost` it opened **no socket at all** — "
         "`/etc/hosts` answered and NSS stopped there. That is the whole reason this is not a "
         "duplicate of `dig`.",
    "‖": "**Two interfaces.** `nsapi` to create and enter — `unshare` plus a bind mount under "
         "`/run/netns` — and `netlink` to list nsids. The bind mount is exactly why it cannot see "
         "Docker's namespaces.",
    "⁂": "**Two interfaces.** `socket` for `s_client`; `local` for everything else (`dgst`, "
         "`genpkey`, `enc`, `x509`), which is pure computation on files.",
}


def slug(tool: str) -> str:
    """`ip netns` -> `ip-netns`. The filename is the URL, so it has to be path-safe."""
    return re.sub(r"[^a-z0-9]+", "-", tool.lower()).strip("-")


def read_index():
    """The topical tables of the index, as records. Table-aware for the same reason
    `index_tool_rows()` in check_pedagogy.py is: the page also carries summary tables whose rows
    are interfaces, not tools."""
    cols, out, section = None, [], ""
    for line in open(INDEX).read().split("\n"):
        st = line.strip()
        if st.startswith("## "):
            section = st[3:].strip()
        if not st.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in st.strip("|").split("|")]
        if "In the course" in cells:
            cols = cells
            continue
        if cols is None or all(set(c) <= {"-", ":"} for c in cells) or len(cells) != len(cols):
            continue
        r = dict(zip(cols, cells))
        names = re.findall(r"`([^`]+)`", r["Tool"])
        sp = r["Speaks"].split("·", 1)
        out.append({
            "id": names[0], "names": names,
            # A linked name claims a page; a bare code span is a row and nothing more. The roster is
            # already the hand-written input that decides which tools exist, so it is the right place
            # to decide which of them earn a page — and de-linking a row is the whole edit, because
            # the orphan sweep in `main()` then deletes the file.
            "page": bool(re.search(r"\]\([^)]+\.md\)", r["Tool"])),
            "one": (r.get("The one thing only it shows you")
                    or r.get("Why it is in a networking reference", "")).strip(),
            "iface": re.sub(r"&nbsp;.*", "", sp[0]).strip(),
            "mark": next((m for m in MARK_NOTE if m in sp[0]), ""),
            "grammar": sp[1].strip() if len(sp) > 1 else "",
            "course": r["In the course"].strip(),
            "section": section,
        })
    return out


def cell(text: str) -> str:
    """Escape pipes so a command containing one does not split into extra table cells.

    Real commands are full of them — `wg genkey | wg pubkey`, `sysctl -a | grep`,
    `ip link set <dev> up | mtu 1400`. Markdown needs `\\|` inside a table cell.
    """
    return text.replace("|", "\\|")


# Where the roster sits, and where a tool page sits, as depths below the repo root. The roster is
# `reference/tools/README.md`; a tool page is `reference/tools/<interface>/<tool>.md`, one directory
# deeper — because the sidebar then groups them by interface without anyone maintaining a list, and
# the interface ends up in the URL, which is where the taxonomy is most useful.
INDEX_UP = "../" * 2
TOOL_UP = "../" * 3


def bump(text: str) -> str:
    """Re-root a relative link copied out of the roster onto a tool page, one directory deeper.

    Derived from the two depths above rather than written out, because the last time this was a
    literal string the roster moved and every one of the seventy-two `Taught in` links quietly
    started pointing at `reference/networking-fundamentals/`, which does not exist.
    """
    return text.replace(f"]({INDEX_UP}networking-fundamentals/",
                        f"]({TOOL_UP}networking-fundamentals/")


# How much work the substitution is. The `swap` facet exists because "superseded" on its own
# tells a reader to stop using something without telling them what it costs to stop, and those
# are three very different costs: `netstat -tulnp` and `ss -tulnp` are the same keystrokes, while
# an `iptables` ruleset and an `nft` one are not the same document.
SWAP = {
    "rename": ("drop-in",
               "**The swap is the name.** The replacement takes the same flag letters, so anything "
               "you can type here works there unchanged."),
    "reflag": ("same job, different invocation",
               "**Same job, different invocation.** A minute to relearn by hand — but a script that "
               "shells out to this one needs editing, not renaming."),
    "rewrite": ("not a drop-in",
                "**Not a drop-in.** A different model and a different output shape, so anything "
                "built on this one gets rebuilt rather than renamed."),
}


def sentence(text):
    """A rationale from the JSON, rendered as prose: capitalised, and closed with a full stop."""
    text = bump(text)
    return text[0].upper() + text[1:] + ("" if text.endswith((".", "!", "`")) else ".")


def supersession_index(data):
    """Which tools are named as the replacement for which — read backwards out of the `by` lists.

    Computed rather than stored, so the two halves cannot disagree: `ss` cannot claim to replace
    `netstat` unless `netstat`'s own page says so. `arp` names `ip neigh`, a command rather than a
    binary, so the key is the first word and the phrase is kept for display.
    """
    idx = {}
    for tool, d in data.items():
        st = d.get("standing", {})
        if st.get("level") != "superseded":
            continue
        for phrase in st.get("by", []):
            idx.setdefault(phrase.split()[0], []).append((tool, phrase))
    return {k: sorted(v) for k, v in idx.items()}


def sibling_link(target, from_iface, rows):
    """Link to another tool's page, which may sit under a different interface directory.

    `netstat` is superseded by `ss`, but they are on different interfaces — which is the whole
    reason one supersedes the other — so the link has to cross directories.
    """
    # `arp` names `ip neigh` as its replacement — a command, not a binary. The page belongs to
    # `ip`, so resolve on the first word and keep the full phrase as the link text.
    binary = target.split()[0]
    row = next((r for r in rows if r["id"] == binary), None)
    # No row, or a row that is only a row: either way there is nothing to link to, and a plain code
    # span is the honest rendering. Without this, compressing a tool to a row would silently turn
    # every sibling's supersession link into a 404.
    if row is None or not row["page"]:
        return f"`{target}`"
    path = f"{slug(binary)}.md" if row["iface"] == from_iface \
        else f"../{row['iface']}/{slug(binary)}.md"
    return f"[`{target}`]({path})"


def page(t, rows, data, lab, sup) -> str:
    d = data.get(t["id"], {"caps": [], "course": []})
    L = []
    title = f"`{t['id']}`"
    if d.get("name") and d["name"] not in ("—", "-"):
        title += f" — {d['name']}"
    L.append(f"# {title}\n")
    L.append(bump(t["one"]) + "\n")

    taught = "**roster only** — named by the roster, run by no lesson" \
        if "roster only" in t["course"] else bump(t["course"])
    L.append("| | |")
    L.append("|---|---|")
    # The interface page is this directory's own README, so the link is a bare filename — which
    # is the point of the move: the taxonomy is the directory tree, not a cross-reference.
    L.append(f"| **Speaks** | [`{t['iface']}`](README.md)"
             + (f" · {t['grammar']}" if t["grammar"] else "") + " |")
    L.append(f"| **Mode** | {' · '.join(d.get('mode', ['read-only']))} |")
    L.append(f"| **Taught in** | {taught} |")

    # In the lab: measured by tools/probe-lab.py, never asserted. A reader who types a command
    # that is not installed should have been told so on the page, not by the shell.
    inv = lab.get(t["id"], {})
    if inv.get("present"):
        ver = f" · {inv['version']}" if inv.get("version") else ""
        # `socat` resolving to `socat1` is a version suffix, not a different implementation;
        # only a genuinely different provider is worth a reader's attention.
        prov = inv.get("provider")
        note = ""
        if prov and not prov.startswith(t["id"]):
            note = " — " + PROVIDER_NOTE.get(prov, f"provided by `{prov}`").format(tool=t["id"])
        L.append(f"| **In the lab** | ✅ `{inv['path']}`{cell(ver)}{cell(note)} |")
    else:
        L.append(f"| **In the lab** | ❌ not installed in `netlab:latest` — "
                 f"you will meet this one outside the lab |")

    st = d.get("standing", {"level": "default"})
    by_links = [sibling_link(b, t["iface"], rows) for b in st.get("by", [])]
    if st["level"] == "superseded":
        cost = SWAP[st["swap"]][0]
        L.append(f"| **Standing** | ⚠️ **superseded** by {' or '.join(by_links)} — {cost} |")
    elif st["level"] == "emerging":
        L.append(f"| **Standing** | 🆕 **emerging** — first released {st['since']}, "
                 f"and you install it deliberately |")

    # The other direction, read out of everyone else's `by` list rather than stored here — so a
    # tool cannot advertise itself as the modern replacement for something without that something
    # agreeing. This is the row that makes the current tools findable, not just the legacy ones.
    if t["id"] in sup:
        reps = " · ".join(
            sibling_link(old, t["iface"], rows)
            # `arp` is replaced by `ip neigh`, not by `ip` — name the object, or the reader
            # arrives on a thirty-object page with no idea which one they wanted.
            + ("" if phrase == t["id"] else f" (as `{phrase}`)")
            for old, phrase in sup[t["id"]])
        L.append(f"| **Supersedes** | ✅ **prefer this one** over {reps} |")

    L.append(f"| **Blind spot** | `{t['iface']}` {IFACE_BLIND[t['iface']]} |")
    L.append(f"| **Also here** | [the roster](../README.md) · "
             f"[by question](../../04-by-question.md) |\n")

    # A reader who lands here from an old runbook wants one thing before the capability tables:
    # what to type instead. So the substitution goes above the fold, with the concrete rewrites
    # first and the justification last — the reverse of the order in which it was decided.
    if st["level"] == "superseded":
        L.append(f"## ⚠️ Prefer {' or '.join(by_links)}\n")
        L.append(SWAP[st["swap"]][1] + "\n")
        if st.get("instead"):
            L.append("| instead of | type this |")
            L.append("|---|---|")
            for a, b in st["instead"]:
                L.append(f"| `{cell(a)}` | `{cell(b)}` |")
            L.append("")
        L.append(f"**What you gain.** {sentence(st['gains'])}\n")
        if st.get("gotcha"):
            L.append(f"**What will bite you in the swap.** {sentence(st['gotcha'])}\n")
        if st.get("but"):
            L.append(f"**Read this one anyway.** {sentence(st['but'])}\n")
        L.append(f"**Why it is marked superseded.** {sentence(st['why'])}\n")
    elif st["level"] == "emerging":
        L.append(f"## 🆕 New, and worth the install\n")
        L.append(f"**What you gain.** {sentence(st['gains'])}\n")
        L.append(f"**Why it is marked emerging.** {sentence(st['why'])}\n")

    if t["mark"]:
        L.append(f"> {MARK_NOTE[t['mark']]}\n")

    # Above the capability tables, because "how do I drive this" is the question a reader has
    # before "what else can it do", and a thirty-row table is not an answer to it. Absent on
    # roughly a third of the roster by design — see `check_keys` in check_pedagogy.py.
    if d.get("keys"):
        L.append("## The flags that carry their weight\n")
        L.append(f"*Not the flag list — `{t['id']} --help` has that. These "
                 f"{len(d['keys'])} change what the tool can **see**.*\n")
        L.append("| Flag | What it changes |")
        L.append("|---|---|")
        for k, why in d["keys"]:
            L.append(f"| `{cell(k)}` | {cell(bump(why))} |")
        L.append("")

    if d["caps"]:
        n = sum(len(cs) for _, cs in d["caps"])
        L.append(f"## What it can do\n")
        L.append(f"*{n} commands, grouped by what you are trying to find out.*\n")
        for g, cs in d["caps"]:
            L.append(f"### {g}\n")
            L.append("| Command | What it gives you |")
            L.append("|---|---|")
            for c, w in cs:
                L.append(f"| `{cell(c)}` | {cell(w)} |")
            L.append("")

    if d["course"]:
        L.append(f"## As the course runs it\n")
        L.append(f"*{len(d['course'])} commands this course actually runs, taken apart. "
                 f"The breakdowns are hand-written.*\n")
        L.append("| Command | Syntax breakdown | Lesson |")
        L.append("|---|---|---|")
        for c in d["course"]:
            L.append(f"| `{cell(c['cmd'])}` | {cell(c['why'])} | {cell(c['lesson'] or c['act'])} |")
        L.append("")

    return "\n".join(L)


def main(argv):
    rows = read_index()
    data = json.load(open(DATA))
    lab = json.load(open(LAB))["tools"]
    sup = supersession_index(data)
    os.makedirs(OUT, exist_ok=True)
    stale, written = [], 0
    for t in rows:
        if not t["page"]:
            continue
        d = os.path.join(OUT, t["iface"])
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, slug(t["id"]) + ".md")
        body = page(t, rows, data, lab, sup)
        old = open(path).read() if os.path.exists(path) else None
        if old == body:
            continue
        if "--check" in argv:
            stale.append(os.path.relpath(path, REPO))
            continue
        open(path, "w").write(body)
        written += 1
    # A tool page for a row that no longer exists is a lie the link checker cannot see. The
    # README.md files are the exception and have to be named explicitly: they are hand-written
    # *input* to this generator — the roster it reads, and the interface page each directory leads
    # with — and an orphan sweep that deleted its own source would be a memorable afternoon.
    keep = {os.path.join(t["iface"], slug(t["id"]) + ".md") for t in rows if t["page"]}
    keep.add("README.md")
    keep |= {os.path.join(i, "README.md") for i in {t["iface"] for t in rows}}
    orphans = []
    for root, _, files in os.walk(OUT):
        for f in files:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(root, f), OUT)
            if rel not in keep:
                orphans.append(rel)
    if "--check" in argv:
        if stale or orphans:
            print("stale: %s" % ", ".join(stale) if stale else "", file=sys.stderr)
            print("orphaned: %s" % ", ".join(orphans) if orphans else "", file=sys.stderr)
            return 1
        print("%d tool pages up to date (%d rows)"
              % (sum(1 for t in rows if t["page"]), len(rows)))
        return 0
    for f in orphans:
        os.remove(os.path.join(OUT, f))
    paged = sum(1 for t in rows if t["page"])
    print("%d tool pages for %d rows (%d rewritten, %d orphans removed)"
          % (paged, len(rows), written, len(orphans)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
