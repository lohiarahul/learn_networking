#!/usr/bin/env python3
"""probe-lab.py — ask the lab image which tools it actually has, and which version.

Writes reference/lab-inventory.json. This is the only source for the index's `In the lab`
column: a tool is present because `command -v` found it in netlab:latest, not because
someone thought it would be there.

It also re-runs every command the reference quotes *output* from (capabilities.json's
`standing.evidence`) and records whether the quoted string still appears, so a base-image
bump falsifies the prose loudly rather than silently.

    python3 tools/probe-lab.py            # regenerate
    python3 tools/probe-lab.py --check    # non-zero if the committed file is stale

Needs Docker and the netlab image (`make -C networking-fundamentals/code` builds it).
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPS = os.path.join(REPO, "reference", "capabilities.json")
OUT  = os.path.join(REPO, "reference", "lab-inventory.json")
IMAGE = "netlab:latest"

# Which tools get asked their version, and how. An allowlist rather than a default of `-V`,
# for two reasons: on a busybox tool `-V` prints "unrecognized option" and on `tshark` it starts
# a live capture. Absence from this table means "presence only, no version" — which is all the
# `In the lab` column needs.
VERSION_CMD = {
    "ip": "-V", "tc": "-V", "iptables": "-V", "iptables-save": "-V", "nft": "--version",
    "ipset": "--version", "conntrack": "--version", "ethtool": "--version",
    "tcpdump": "--version", "socat": "-V", "curl": "--version", "openssl": "version",
    "dig": "-v", "host": "-V", "nslookup": "-version", "nmap": "--version",
    "iperf3": "--version", "mtr": "--version", "strace": "-V", "ltrace": "-V",
    "jq": "--version", "lsof": "-v", "nsenter": "--version", "unshare": "--version",
    "mount": "-V", "ping": "-V", "ipvsadm": "--version", "python3": "--version",
    "bpftool": "version", "bpftrace": "--version", "devlink": "-V", "wg": "--version",
    "kubectl": "version --client=true -o yaml", "helm": "version --short",
    "crictl": "--version", "runc": "--version", "docker": "--version", "kind": "--version",
    "kubeadm": "version -o short", "etcdctl": "version", "etcdutl": "version",
    "trivy": "--version", "cosign": "version", "crane": "version", "falco": "--version",
    "kustomize": "version", "cilium": "version --client", "capsh": "--version",
    "apparmor_parser": "--version", "kube-bench": "version", "pwru": "--version",
    "retis": "--version",
}

def tools():
    with open(CAPS) as f:
        return sorted(json.load(f))

def probe(names):
    """One container, one shell: `command -v` then the version flag for whatever was found."""
    script = ["set -f"]
    for n in names:
        # A few index entries are commands rather than binaries ("ip netns", "getent hosts").
        # Presence is decided by the binary, which is the first word.
        binary = n.split()[0]
        flag = VERSION_CMD.get(n)
        script.append(f'p=$(command -v {binary} 2>/dev/null) || p=""')
        if flag:
            # timeout, because an unknown flag makes some of these block on a DNS lookup
            script.append(f'v=$([ -n "$p" ] && timeout 5 {n} {flag} 2>&1 </dev/null | head -1) || v=""')
        else:
            script.append('v=""')
        # What the name actually resolves to. Alpine hands you BusyBox applets for several of
        # these — `/bin/netstat` is a symlink to `/bin/busybox` — and a BusyBox applet implements
        # a subset of the flags the tool page lists, so the page has to say so. Measured with
        # readlink -f rather than assumed from the distro.
        script.append('r=$([ -n "$p" ] && readlink -f "$p") || r=""')
        script.append(f'[ -n "$p" ] && printf "%s\\t%s\\t%s\\t%s\\n" "{n}" "$p" "$v" "$r" '
                      f'|| printf "%s\\t\\t\\t\\n" "{n}"')
    r = subprocess.run(["docker", "run", "--rm", "--entrypoint", "sh", IMAGE, "-c",
                        "\n".join(script)], capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout.strip():
        sys.exit(f"probe-lab: could not run {IMAGE}: {r.stderr.strip()[:300]}")
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, path, ver = parts[0], parts[1], parts[2].strip()
        real = parts[3].strip() if len(parts) > 3 else ""
        rec = {"present": bool(path), "path": path,
               "version": re.sub(r"\s+", " ", ver)[:120] if path else ""}
        # Only recorded when the name is not its own implementation, which is the case worth
        # telling a reader about. `/sbin/ip` resolving to `/sbin/ip` is not news.
        if real and os.path.basename(real) != os.path.basename(path):
            rec["provider"] = os.path.basename(real)
        out[name] = rec
    return out

def evidence(caps):
    """Re-run the commands the reference *quotes output from*, and record whether it still holds.

    A prose field that quotes in-image output — `arp -6` answering `unrecognized option: 6`, an
    unprepared `nft` answering `Could not process rule` — is a measurement with an expiry date:
    one `apk add net-tools` or one base-image bump and the reference is confidently wrong with
    every check still green. So each such claim declares itself in capabilities.json under
    `standing.evidence`, and this function is the thing that keeps it true.

    Each claim runs in its *own* fresh container, deliberately: the `nft` gotcha is a claim about
    a host with no tables yet, and a claim like that cannot be measured after an earlier command
    in the same shell has created some.
    """
    out = {}
    for tool in sorted(caps):
        for e in caps[tool].get("standing", {}).get("evidence", []):
            cmd = e["cmd"]
            # `--privileged` only where the claim is about a privileged operation failing for a
            # reason that is not permissions: unprivileged, `nft` says "you must be root", which
            # would make the check pass for the wrong reason.
            run = ["docker", "run", "--rm"] + (["--privileged"] if e.get("root") else []) \
                + ["--entrypoint", "sh", IMAGE, "-c", f"{cmd} 2>&1"]
            r = subprocess.run(run, capture_output=True, text=True)
            text = r.stdout + r.stderr
            lines = [l for l in text.splitlines() if l.strip()]
            matched = all(x in text for x in e["expect"])
            rec = {"cmd": cmd, "expect": e["expect"], "matched": matched}
            # An excerpt only when the claim has *failed*, and for two reasons. It is the case a
            # human needs to look at — "so what does it say now?" — and it is the only case where
            # churn is free: some of this output carries per-run numbers (`ss` prints a live
            # `rtt:`), so storing it on the happy path would make --check fail on nothing.
            if not matched and lines:
                rec["got"] = re.sub(r"\s+", " ", lines[0])[:160]
            out.setdefault(tool, []).append(rec)
    return out

def main(argv):
    names = tools()
    with open(CAPS) as f:
        caps = json.load(f)
    inv = probe(names)
    missing = [n for n in names if n not in inv]
    if missing:
        sys.exit(f"probe-lab: no result for {len(missing)} tool(s): {', '.join(missing[:8])}")
    doc = {"image": IMAGE,
           "present": sum(1 for v in inv.values() if v["present"]),
           "total": len(inv),
           "evidence": evidence(caps),
           "tools": inv}
    text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        old = open(OUT).read() if os.path.exists(OUT) else ""
        if old != text:
            print(f"probe-lab: {os.path.relpath(OUT, REPO)} is stale — rerun tools/probe-lab.py")
            return 1
        claims = sum(len(v) for v in doc["evidence"].values())
        print(f"✓ lab inventory current: {doc['present']}/{doc['total']} present in {IMAGE}, "
              f"{claims} quoted-output claim(s) re-measured")
        return 0
    with open(OUT, "w") as f:
        f.write(text)
    bad = [(t, c["cmd"]) for t, v in doc["evidence"].items() for c in v if not c["matched"]]
    print(f"wrote {os.path.relpath(OUT, REPO)}: {doc['present']}/{doc['total']} present in {IMAGE}")
    for t, cmd in bad:
        print(f"  ⚠️  `{t}` quotes output that {IMAGE} no longer produces: {cmd}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
