"""The course as a graph, built once, so ordering questions become graph questions.

WHY A GRAPH
-----------
The three rules this course is held to are all statements about *order*, and the monolith could
only check two of them, because it read one file at a time:

* **Ladder** — the "you can now" lines must form an unbroken staircase. Checkable per file, and
  the monolith did: does this lesson have a milestone and a forward pointer?
* **Spirit** — does the passage keep the reader's drive alive? Not mechanisable, and correctly
  left to the `learner-simulator` agent.
* **River** — *nothing may use a concept not yet introduced.* This one was given up on entirely,
  with a stated reason: "lexical checks produce false positives on exactly the best-written
  lessons." That reason is right about *prose* and wrong about *commands*. A lesson that writes
  "we will meet `nft` in Act IV" has not used `nft`; a lesson with `nft list ruleset` in a fenced
  block has. The distinction is structural, not semantic — so it is decidable.

River is a reachability property over a DAG: order the lessons, mark where each tool is
*introduced*, and any use at a lower order index is uphill flow. `capabilities.json` already
records the introduction points (its `course[]` entries name act and lesson), so this needs no
new authoring — it reads data the repo has been maintaining all along for another purpose.

This is a curriculum prerequisite network, which is a well-trodden shape: nodes are units, edges
are prerequisites, and a valid reading order is a topological sort of it. Cycle detection matters
for the same reason it does there — a cycle means two lessons each require the other, and no
reading order exists.

WHAT IS DELIBERATELY NOT MODELLED
---------------------------------
Concepts that are not tools. "conntrack the idea" is introduced in Act III and reused in Acts IV,
V and VIII, and no file records that. Modelling it needs a concept registry someone has to
author, and a half-populated one would produce confident wrong answers. The graph covers tools,
says so, and reports its own coverage rather than implying it checked everything.
"""
from __future__ import annotations
import functools, json, os, re
from dataclasses import dataclass, field

from .corpus import commands_only, lesson_files, read, strip_code, LINK_RE
from .model import READING_ORDER
from .paths import CAPS_JSON, COURSE, rel

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
         "VII": 7, "VIII": 8, "IX": 9, "X": 10}
PRE_COURSE = "<lab setup>"   # introduced before lesson one; no lesson file to name
ACT_LABEL_RE = re.compile(r"^Act\s+([IVX]+)\b")
LESSON_LABEL_RE = re.compile(r"^Lesson\s+(\d+)([a-z]?)\b")


@dataclass(frozen=True)
class Lesson:
    path: str
    act: str
    number: str          # "05b"
    order: int           # position in the whole course


@dataclass
class Graph:
    lessons: dict[str, Lesson] = field(default_factory=dict)          # rel path -> Lesson
    act_order: dict[str, int] = field(default_factory=dict)
    introduces: dict[str, str] = field(default_factory=dict)          # tool -> rel path
    intro_order: dict[str, int] = field(default_factory=dict)         # tool -> order (-1 = lab)
    unresolved: list[tuple[str, str, str]] = field(default_factory=list)  # tool, act, lesson
    uses: dict[str, set[str]] = field(default_factory=dict)           # tool -> {rel path}
    cites: dict[str, set[str]] = field(default_factory=dict)          # rel path -> {rel path}

    def order_of(self, rel_path: str) -> int | None:
        lesson = self.lessons.get(rel_path)
        return lesson.order if lesson else None


def _act_dir(label: str) -> str | None:
    m = ACT_LABEL_RE.match(label or "")
    if not m:
        return None
    n = ROMAN.get(m.group(1))
    if n is None:
        return None
    for act in READING_ORDER:
        if act.startswith(f"act-{n}-"):
            return act
    return None


def _lesson_prefix(label: str) -> str | None:
    m = LESSON_LABEL_RE.match(label or "")
    if not m:
        return None
    return f"{int(m.group(1)):02d}{m.group(2)}"


@functools.lru_cache(maxsize=1)
def build() -> Graph:
    g = Graph()

    for i, act in enumerate(READING_ORDER):
        g.act_order[act] = i

    order = 0
    for act in READING_ORDER:
        act_dir = os.path.join(COURSE, act)
        if not os.path.isdir(act_dir):
            continue
        for path in sorted(lesson_files()):
            if os.path.dirname(path) != act_dir:
                continue
            base = os.path.basename(path)
            g.lessons[rel(path)] = Lesson(path=rel(path), act=act,
                                          number=base.split("-")[0], order=order)
            order += 1

    by_prefix = {}
    for r, lesson in g.lessons.items():
        by_prefix[(lesson.act, lesson.number)] = r

    # Introduction points, from the data the reference wing already maintains.
    if os.path.exists(CAPS_JSON):
        caps = json.load(open(CAPS_JSON, encoding="utf-8"))
        for tool, spec in caps.items():
            best = None
            for entry in spec.get("course") or []:
                act_label = entry.get("act", "")
                # A citation with no act is lab setup ("Starting the lab") — the reader has the
                # tool before lesson one, so it is introduced at order -1 rather than unresolved.
                # `docker` is the case that matters: four of its eleven citations are lab setup,
                # and skipping them made the lab substrate look like it arrived in Act I lesson 5.
                if not act_label.strip():
                    best = (-1, PRE_COURSE)
                    break
                act = _act_dir(act_label)
                pre = _lesson_prefix(entry.get("lesson", ""))
                if not act or not pre:
                    continue
                target = by_prefix.get((act, pre))
                if target is None:
                    g.unresolved.append((tool, entry.get("act", ""), entry.get("lesson", "")))
                    continue
                o = g.lessons[target].order
                if best is None or o < best[0]:
                    best = (o, target)
            if best:
                g.introduces[tool] = best[1]
                g.intro_order[tool] = best[0]

    # Uses, counted only inside code — a mention is not a use.
    for tool in g.introduces:
        pattern = re.compile(r"(?:^|[\s|;&(`$])" + re.escape(tool) + r"(?=[\s|;&)`]|$)",
                             re.MULTILINE)
        for r, lesson in g.lessons.items():
            if pattern.search(commands_only(read(os.path.join(COURSE, "..", r)))):
                g.uses.setdefault(tool, set()).add(r)

    # Citations, for reachability.
    for r in g.lessons:
        src = os.path.join(COURSE, "..", r)
        targets = set()
        for t in LINK_RE.findall(strip_code(read(src))):
            t = t.strip().split("#")[0]
            if not t or t.startswith(("http", "mailto")):
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(src), t))
            targets.add(rel(resolved))
        g.cites[r] = targets

    return g


def coverage() -> dict:
    g = build()
    return {"lessons": len(g.lessons),
            "tools_with_introduction": len(g.introduces),
            "unresolved_citations": len(g.unresolved)}
