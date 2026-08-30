"""`capabilities.json` — standing, keys, and the evidence behind a supersession claim.

The largest cluster in the harness, and the one whose logic is most intricate: it reasons
about whether a tool the course recommends is still the right recommendation, and whether
the repo can show its work. Moved verbatim from the monolith for exactly that reason.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import datetime, json, os, re
from ..corpus import read
from ..model import EMERGING_YEARS, INTERFACES, MAX_KEYS, STANDING_LEVELS, SWAP_KINDS
from ..paths import CAPS_JSON, INDEX_MD, LAB_JSON, rel


def check_standing(_files):
    """Warning-only: the `Standing` facet must stay a measurement, not an opinion.

    The facet answers "is this tool current, or am I only meeting it because other people's
    runbooks are full of it?" — which is worth having only if every non-default verdict names its
    evidence. So the shape is enforced:

      * the vocabulary is closed (default / superseded / emerging), like `Speaks` and `Mode`;
      * `superseded` must name a replacement that is itself on the roster — "superseded" with no
        successor is a complaint, not a fact;
      * `emerging` must carry a first-release year, and must *not* be installed in the lab image,
        because "you install it deliberately" is the claim the level makes;
      * every non-default verdict carries a rationale long enough to be an argument.

    Also checks that the measured inventory covers exactly the roster, so a tool added to
    capabilities.json without rerunning tools/probe-lab.py is caught rather than silently
    rendering as "not installed".
    """
    import json
    issues = []
    if not (os.path.exists(CAPS_JSON) and os.path.exists(LAB_JSON)):
        return [("WARN", "standing: capabilities.json or lab-inventory.json missing")]
    issues += check_standing_section()
    with open(CAPS_JSON) as f: caps = json.load(f)
    with open(LAB_JSON) as f: lab = json.load(f)
    inv = lab.get("tools", {})

    missing = sorted(set(caps) - set(inv))
    extra = sorted(set(inv) - set(caps))
    if missing:
        issues.append(("WARN", f"standing: lab-inventory.json has no measurement for "
                               f"{len(missing)} tool(s) ({', '.join(missing[:6])}) — "
                               f"rerun tools/probe-lab.py"))
    if extra:
        issues.append(("WARN", f"standing: lab-inventory.json measures {len(extra)} tool(s) no "
                               f"longer on the roster ({', '.join(extra[:6])})"))

    for tool in sorted(caps):
        st = caps[tool].get("standing")
        if not st:
            issues.append(("WARN", f"standing: `{tool}` has no standing facet"))
            continue
        lvl = st.get("level")
        if lvl not in STANDING_LEVELS:
            issues.append(("WARN", f"standing: `{tool}` has level {lvl!r}, outside the closed "
                                   f"vocabulary {sorted(STANDING_LEVELS)}"))
            continue
        if lvl == "default":
            continue
        why = st.get("why", "")
        if len(why) < 80:
            issues.append(("WARN", f"standing: `{tool}` is marked {lvl} with a "
                                   f"{len(why)}-character rationale — name the evidence"))
        if lvl == "superseded":
            by = st.get("by") or []
            if not by:
                issues.append(("WARN", f"standing: `{tool}` is superseded by nothing named"))
            for b in by:
                if b.split()[0] not in caps:
                    issues.append(("WARN", f"standing: `{tool}` is superseded by `{b}`, which is "
                                           f"not on the roster"))
            # "Superseded" without a migration cost is advice a reader cannot act on: whether the
            # swap is a rename, a relearn or a rewrite is the whole difference between "do it now"
            # and "schedule it". So the cost is required, and so is at least one worked rewrite.
            if st.get("swap") not in SWAP_KINDS:
                issues.append(("WARN", f"standing: `{tool}` is superseded with swap "
                                       f"{st.get('swap')!r}, outside {sorted(SWAP_KINDS)}"))
            instead = st.get("instead") or []
            if not instead:
                issues.append(("WARN", f"standing: `{tool}` is superseded with no `instead` "
                                       f"rewrites — name what to type instead"))
            for pair in instead:
                if not (isinstance(pair, list) and len(pair) == 2):
                    issues.append(("WARN", f"standing: `{tool}` has a malformed `instead` entry "
                                           f"{pair!r} — want [old, new]"))
                    continue
                old_cmd, new_cmd = pair
                # The left side must be this tool, or the row is telling you to stop using
                # something else; the right side must be a tool on the roster, or the reference
                # is sending you to a page that does not exist.
                if old_cmd.split()[0] != tool:
                    issues.append(("WARN", f"standing: `{tool}`'s `instead` row starts "
                                           f"`{old_cmd}`, which is not this tool"))
                if new_cmd.split()[0] not in caps:
                    issues.append(("WARN", f"standing: `{tool}`'s `instead` row points at "
                                           f"`{new_cmd}`, whose tool is not on the roster"))
        issues += check_evidence(tool, st, lab.get("evidence", {}).get(tool, []))
        # `gains` is the field that makes the verdict useful rather than merely disapproving:
        # what the reader gets, not what the reader loses. Required at both non-default levels.
        if len(st.get("gains", "")) < 60:
            issues.append(("WARN", f"standing: `{tool}` is marked {lvl} without saying what the "
                                   f"reader gains — that is a complaint, not a recommendation"))
        if lvl == "emerging":
            yr = st.get("since")
            if not (isinstance(yr, int) and 1990 <= yr <= 2100):
                issues.append(("WARN", f"standing: `{tool}` is emerging with since={yr!r} — "
                                       f"needs a four-digit first-release year"))
            if inv.get(tool, {}).get("present"):
                issues.append(("WARN", f"standing: `{tool}` is marked emerging but the lab image "
                                       f"now ships it — it has become a default"))
            # "Emerging" is a claim about *now* — new enough that you install it deliberately —
            # stored as a static year, which means it is the one facet guaranteed to rot: nothing
            # about `pwru` will change on its own, and in 2031 the page will still be calling a
            # ten-year-old tool new. The year stays in the page, because the year is a fact; the
            # judgement of whether it is still recent belongs here, where it can be re-read
            # against today rather than against the day someone typed it.
            elif isinstance(yr, int) and datetime.date.today().year - yr > EMERGING_YEARS:
                issues.append(("WARN", f"standing: `{tool}` is marked emerging but was first "
                                       f"released {yr}, "
                                       f"{datetime.date.today().year - yr} years ago — re-read "
                                       f"the verdict: still a deliberate install, or just "
                                       f"unpackaged?"))
    return issues


def key_literal(key):
    """The typable part of a `keys` entry. A flag is documented with its argument where that is
    how you meet it — `-e trace=<set>`, `-M do` — but the thing that has to appear in a command
    is the flag itself."""
    return re.split(r"[ <]", key, maxsplit=1)[0].strip()


def flag_used(key, cmds):
    """Is this flag actually typed in one of the commands on the tool's own page?"""
    lit = key_literal(key)
    for c in cmds:
        for tok in re.split(r"[\s|'\"]+", c):
            tok = tok.split("=", 1)[0].split(":", 1)[0]
            if tok == lit:
                return True
            # `dig` drives on `+trace` and `@1.1.1.1`, neither of which is a dash-flag.
            if lit[:1] in "+@" and tok.startswith(lit):
                return True
            # Short-flag bundling, because getopt permits it and this course uses it throughout:
            # `ss -i` is only ever typed as `ss -ti`, `ulimit -H` as `-Hn`, `nstat -z` as `-az`.
            if len(lit) == 2 and lit[0] == "-" and lit[1].isalnum() \
               and tok.startswith("-") and not tok.startswith("--") and lit[1] in tok[1:]:
                return True
    return False


def check_keys(_files):
    """Warning-only: the `keys` facet must name flags the page also demonstrates.

    The facet exists because `--help` sorts flags alphabetically and treats all forty as equals,
    which is the opposite of what a reader needs. The editorial rule is that a flag earns a line
    only when leaving it off gives you a different *answer* rather than a different format:
    `ip -d` is the only way an interface's kind appears at all, while `ip -j` is the same facts in
    JSON. So `-j`, `-br` and `jq`'s pretty-printer are in the capability tables and not here.

    Which makes the facet sparse on purpose. Roughly a third of the roster names nothing, because
    a tool driven by objects and subcommands — `bridge fdb show`, `wg show`,
    `socat TCP-LISTEN:8080,fork -` — has no flag that carries weight, and inventing one would
    bury the ones that do. Absence is a claim here, so it is not flagged.

    What is enforced:

      * every flag named must be typed in one of that tool's own commands, so the reader has a
        worked example rather than a flag they have to go and look up. This is the check that
        keeps the facet from drifting into a transcription of `--help`;
      * at most four, since a list of ten is the thing this facet exists to replace;
      * no duplicates, and a rationale long enough to say what changes rather than what the flag
        is called;
      * nothing on a superseded tool. That page's job is the swap table — it is telling the reader
        to stop typing this command, and a section on how to type it better fights the page.
    """
    import json
    issues = []
    if not os.path.exists(CAPS_JSON):
        return []
    with open(CAPS_JSON) as f: caps = json.load(f)
    for tool in sorted(caps):
        d = caps[tool]
        keys = d.get("keys")
        if not keys:
            continue
        if d.get("standing", {}).get("level") == "superseded":
            issues.append(("WARN", f"keys: `{tool}` is superseded and still names key flags — "
                                   f"that page's job is the swap table, not how to drive this one"))
        if len(keys) > MAX_KEYS:
            issues.append(("WARN", f"keys: `{tool}` names {len(keys)} flags, over the {MAX_KEYS} "
                                   f"this facet exists to cut down to"))
        seen = set()
        cmds = [c for _, cs in d.get("caps", []) for c, _ in cs] \
            + [c["cmd"] for c in d.get("course", [])]
        for k, why in keys:
            if k in seen:
                issues.append(("WARN", f"keys: `{tool}` names `{k}` twice"))
            seen.add(k)
            if len(why) < 40:
                issues.append(("WARN", f"keys: `{tool}` `{k}` has a {len(why)}-character "
                                       f"rationale — say what it changes, not what it is called"))
            if not flag_used(k, cmds):
                issues.append(("WARN", f"keys: `{tool}` names `{k}` as a flag that carries its "
                                       f"weight, but no command on its page types it — either "
                                       f"add the command or drop the flag"))
    return issues


def check_evidence(tool, st, measured):
    """Warning-only: a prose field that quotes in-image output must still produce that output.

    This is the gap the rest of `check_standing` cannot close. Everything above checks *shape* —
    that a level is in the vocabulary, that a successor is on the roster, that a rationale is long
    enough to be an argument. None of it can tell that `arp -6` no longer answers
    `unrecognized option: 6`, and a quoted string is the most convincing sentence on the page and
    the first to go stale: one `apk add net-tools` in the Dockerfile and the reference is
    confidently wrong with every check green.

    So the claim declares itself — `standing.evidence` names the field, the command and the
    string — and this check joins the two halves:

      * the quoted string must actually appear in the field that is said to quote it, so evidence
        cannot drift away from the prose it is evidence *for*;
      * `tools/probe-lab.py` must have re-run the command and found the string, so the prose
        cannot drift away from the image.

    The measurement itself lives in probe-lab, not here, because it needs Docker. What is checked
    here is that a measurement exists, is current, and says yes.
    """
    issues = []
    declared = st.get("evidence", [])
    by_cmd = {m["cmd"]: m for m in measured}
    for e in declared:
        field, cmd, expect = e.get("field"), e.get("cmd"), e.get("expect") or []
        if field not in st:
            issues.append(("WARN", f"evidence: `{tool}` measures {cmd!r} for field {field!r}, "
                                   f"which its standing does not have"))
            continue
        for x in expect:
            if x not in st[field]:
                issues.append(("WARN", f"evidence: `{tool}`'s `{field}` is said to quote {x!r} "
                                       f"but does not — the evidence has drifted from the claim"))
        m = by_cmd.get(cmd)
        if m is None:
            issues.append(("WARN", f"evidence: `{tool}` quotes the output of `{cmd}` but "
                                   f"lab-inventory.json has no measurement of it — rerun "
                                   f"tools/probe-lab.py"))
        elif not m.get("matched"):
            got = m.get("got", "")
            issues.append(("WARN", f"evidence: `{tool}`'s `{field}` quotes output the lab image "
                                   f"no longer produces — `{cmd}` now says {got!r}. The prose is "
                                   f"wrong, not the measurement"))
        elif m.get("expect") != expect:
            issues.append(("WARN", f"evidence: `{tool}`'s measurement of `{cmd}` was taken "
                                   f"against {m.get('expect')!r}, not the current "
                                   f"{expect!r} — rerun tools/probe-lab.py"))
    for cmd in by_cmd:
        if cmd not in {e.get("cmd") for e in declared}:
            issues.append(("WARN", f"evidence: lab-inventory.json measures `{cmd}` for `{tool}`, "
                                   f"which no longer claims it — rerun tools/probe-lab.py"))
    return issues


SECTION_H2 = "## Six to stop reaching for, and two to start"


def check_standing_section():
    """Warning-only: the roster's supersession compartment must name exactly the non-default tools.

    The same bidirectional check `check_index_facets` runs on the interface summary, for the same
    reason: a summary that is allowed to fall behind the rows it summarises is worse than no
    summary, because a reader trusts it. So a tool marked superseded or emerging in
    capabilities.json must appear in the section, and the section must name nothing else.

    Only the *left-hand* superseded name is looked for — the section links successors too, and
    `ss` appearing there is not a claim that `ss` is legacy.
    """
    import json, re as _re
    if not os.path.exists(INDEX_MD):
        return []   # check_reference_shape has already failed the run
    text = read(INDEX_MD)
    if SECTION_H2 not in text:
        return [("WARN", f"standing-section: {rel(INDEX_MD)} has no {SECTION_H2!r} section — "
                         f"the roster no longer says which tools are legacy")]
    body = text.split(SECTION_H2, 1)[1].split("\n## ", 1)[0]
    with open(CAPS_JSON) as f:
        caps = json.load(f)
    want = {t for t, d in caps.items()
            if d.get("standing", {}).get("level", "default") != "default"}
    # Rows are `| [`ss`](…) | [`netstat`](…) | …`; the second cell holds the tool being retired,
    # and the emerging table's first cell holds the tool being recommended. A tool link from the
    # roster is `<interface>/<tool>.md`, since the roster now sits above those directories rather
    # than beside them — matched against the interface names so an ordinary prose link cannot pass
    # for a tool page.
    named = set(_re.findall(r"\[`([a-z0-9_.-]+)`\]\((?:" + "|".join(INTERFACES) + r")/", body))
    missing = sorted(want - named)
    if missing:
        issues = [("WARN", f"standing-section: {', '.join(missing)} marked non-default in "
                           f"capabilities.json but absent from {SECTION_H2!r}")]
    else:
        issues = []
    return issues
