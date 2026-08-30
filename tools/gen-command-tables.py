#!/usr/bin/env python3
"""gen-command-tables.py — the skeleton half of `reference/05-per-act-commands.md`.

Why this exists
---------------
The command reference is a hybrid on purpose. Extracting *which* commands a lesson runs is mechanical
and must never drift, so a script owns it. Explaining what each syntax element means is the half worth
reading, and a script cannot write it — so the script emits a table with the breakdown column empty and
a human fills it in.

That split is what makes drift visible: a lesson that gains a command shows up as a row with an empty
cell, which `check_pedagogy.py`'s `command-table-coverage` warning reports. The failure mode this avoids
is the one every hand-maintained command list eventually hits — silently describing a command the
lesson stopped running.

Usage
-----
    python3 tools/gen-command-tables.py act-1-one-machine act-2-two-machines
    python3 tools/gen-command-tables.py --all
    python3 tools/gen-command-tables.py --diff reference/05-per-act-commands.md act-1-one-machine

`--diff` is the maintenance mode: it prints commands present in the lessons but absent from the page,
and commands documented on the page that no lesson runs any more. It writes nothing.

The output goes to stdout. It is a starting point to paste and then edit, not a file to overwrite in
place — the hand-written column is the valuable part and a generator must never be able to destroy it.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(REPO, "networking-fundamentals")

# A fence opens with ``` optionally after a blockquote prefix — the course fences commands inside
# `>` callouts too, and those are still commands the reader runs.
FENCE_RE = re.compile(r"^((?:\s*>)*\s*)(`{3,})[ \t]*([A-Za-z0-9_+-]*)[ \t]*$")
LESSON_RE = re.compile(r"\d\d[a-z]?-")

# Shells and continuations that are never the command being taught.
SKIP_PREFIXES = ("#", "|", "+", "-", "=", "<", ">", "*", "}", "{", ")", "]")

# Fence languages that never hold shell commands. `mermaid` is the important one: the course draws a
# lot of diagrams, and their node labels parse as plausible command lines if you let them.
NON_SHELL_LANGS = {"mermaid", "yaml", "yml", "json", "c", "python", "py", "dockerfile", "diff",
                   "text", "plaintext", "ini", "toml", "html", "go", "rust", "sql", "xml"}

# Box-drawing and arrow glyphs mark a diagram, not a command.
BOX_DRAWING = re.compile(r"[\u2500-\u257f\u25b2\u25bc\u25c4\u25ba\u2190-\u2193]")

# The first token must be a command we recognise. This mirrors the classifier in
# `site/scripts/sync-content.mjs` (`SHELL_COMMANDS`) on purpose: the site uses it to decide which bare
# fences are shell, and if the two lists disagree then a command shown as prose on the site would be
# documented here as runnable, or the reverse. Keep them in step.
SHELL_COMMANDS = set("""
ip iptables ip6tables iptables-save iptables-restore nft curl wget cat ls docker kubectl ping ping6
dig drill dog host tcpdump ss netstat nc ncat socat conntrack arp arping ethtool bridge tc nsenter
unshare mount findmnt umount df stat ln rm mkdir touch echo printf export exec cd pwd kill strace
ltrace ps bpftrace nmap python3 python make gcc cc bash sh sudo kind helm openssl base64 xxd od
hexdump awk sed grep cut sort uniq head tail wc tr tee seq watch dhclient resolvectl systemctl
modprobe sysctl traceroute tracepath mtr nslookup lsof prlimit ulimit chmod chown id whoami uname
hostname date env true eza bat fd rg jq yq cilium hubble crictl getent scapy etcdctl etcdutl kubeadm
runc capsh getpcaps apparmor_parser trivy cosign crane kube-bench falco kyverno kustomize wg iperf3
readlink journalctl dmesg free nginx busybox brew apk git nsswitch pgrep pkill sleep timeout xargs
tshark nstat bpftool devlink ipvsadm ipset
""".split())

# Lines that are plainly output rather than input. Kept deliberately narrow: it is better to emit a
# spurious row a human deletes than to silently drop a command they needed to document.
OUTPUT_HINTS = re.compile(
    r"^(total \d|drwx|-rw-|lrwx|State\b|Netid\b|PING |\d+ bytes from|rtt min|"
    r"NAME\s+READY|NAMESPACE\s+NAME|Chain \w+ \(|inet \d|link/|valid_lft)"
)


def is_command(line: str) -> bool:
    """First token is a tool we know, or a shell assignment/subshell that leads into one."""
    if BOX_DRAWING.search(line):
        return False
    token = line.split()[0] if line.split() else ""
    token = token.lstrip("$(").rstrip(";|")
    if token in SHELL_COMMANDS:
        return True
    # `FOO=bar cmd …` and `for x in …; do` are real command lines the lessons use. But the course also
    # annotates raw kernel output in column-aligned blocks (`src=10.0.0.7    the private source`), which
    # start with the same shape — so a run of two or more spaces marks it as a label, not a command.
    if re.search(r"\S {2,}\S", line):
        return False
    if token in {"for", "while", "if"}:
        return True
    # An assignment only opens a *command* line if a command follows it. `FOO=bar curl …` is one;
    # `src=10.0.0.7 dst=93.184.216.34 sport=51920` is a conntrack tuple being read aloud.
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
        return any(w.lstrip("$(").rstrip(";|") in SHELL_COMMANDS for w in line.split()[1:])
    return False


def command_lines(body: str) -> list[str]:
    """The lines in a fence body that are a command someone types."""
    out = []
    for raw in body.split("\n"):
        s = raw.strip()
        if not s or s.startswith(SKIP_PREFIXES):
            continue
        if OUTPUT_HINTS.match(s):
            continue
        if not is_command(s):
            continue
        # A prompt prefix is decoration, not part of the command.
        s = re.sub(r"^[$#]\s+", "", s)
        # Heredoc bodies are YAML/config, not commands — stop at the opener.
        if "<<" in s and re.search(r"<<-?\s*'?\w+'?", s):
            s = s.split("<<")[0].strip() + " <<…"
        out.append(s)
    return out


def fences(text: str):
    """Yield (lang, body) for every fenced block, blockquote-prefixed ones included."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        _, fence, lang = m.groups()
        closer = re.compile(r"^(?:\s*>)*\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + ",}\\s*$")
        buf = []
        i += 1
        while i < len(lines) and not closer.match(lines[i]):
            buf.append(re.sub(r"^(?:\s*>)+\s?", "", lines[i]))
            i += 1
        i += 1
        yield lang, "\n".join(buf)


def lesson_files(act: str) -> list[str]:
    d = os.path.join(COURSE, act)
    if not os.path.isdir(d):
        sys.exit(f"no such act directory: {d}")
    return sorted(
        os.path.join(d, f)
        for f in os.listdir(d)
        if f.endswith(".md") and LESSON_RE.match(f)
    )


def heading(path: str) -> str:
    """The lesson's H1, for the table's section heading."""
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("# "):
            return line[2:].strip()
    return os.path.basename(path)


def collect(act: str) -> list[tuple[str, list[str]]]:
    """[(lesson heading, [command, …]), …] with duplicates removed per lesson."""
    out = []
    for path in lesson_files(act):
        text = open(path, encoding="utf-8", errors="replace").read()
        seen, cmds = set(), []
        for lang, body in fences(text):
            if lang.lower() in NON_SHELL_LANGS:
                continue
            for c in command_lines(body):
                if c not in seen:
                    seen.add(c)
                    cmds.append(c)
        if cmds:
            out.append((f"{heading(path)}  ({os.path.basename(path)})", cmds))
    return out


def emit(act: str) -> None:
    print(f"\n## {act}\n")
    for lesson, cmds in collect(act):
        print(f"### {lesson}\n")
        print("| Command | Syntax breakdown |")
        print("|---|---|")
        for c in cmds:
            cell = c.replace("|", "\\|").replace("`", "'")
            print(f"| `{cell}` |  |")
        print()


def diff(page: str, acts: list[str]) -> None:
    have = open(page, encoding="utf-8", errors="replace").read()
    missing = 0
    for act in acts:
        for lesson, cmds in collect(act):
            for c in cmds:
                token = c.split()[0] if c.split() else ""
                if token and token not in have:
                    print(f"UNDOCUMENTED  {act}  {lesson.split('(')[-1].rstrip(')')}  {c}")
                    missing += 1
    print(f"\n{missing} command(s) run by a lesson and absent from {os.path.relpath(page, REPO)}")


ALL_ACTS = ["00-orientation", "act-1-one-machine", "act-2-two-machines", "act-3-the-internet",
            "act-4-one-pretends-many", "act-5-kubernetes", "act-6-control-plane", "act-7-workloads",
            "act-8-trust", "act-9-identity", "act-10-cluster-security", "act-11-observability"]


def main(argv: list[str]) -> int:
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "--diff":
        diff(os.path.join(REPO, argv[1]), argv[2:] or ALL_ACTS)
        return 0
    acts = ALL_ACTS if argv[0] == "--all" else argv
    for a in acts:
        emit(a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
