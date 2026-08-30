#!/usr/bin/env node
/**
 * sync-content.mjs — project the course Markdown into Starlight content.
 *
 * The lessons in `networking-fundamentals/` stay the single source of truth: they are still plain
 * Markdown, still checked by `tools/check_pedagogy.py`, still readable on GitHub. This script is a
 * one-way projection of those files into `src/content/docs/`, adding only what Starlight needs:
 *
 *   1. Frontmatter (title from the H1, description from the opening paragraph, sidebar order/label).
 *   2. The H1 removed from the body — Starlight renders `title` as the page's <h1>, so leaving the
 *      original in place would print it twice.
 *   3. Relative `.md` links rewritten to site URLs (`01-the-fd-table.md` -> `/act-1/the-fd-table/`).
 *
 * Everything else — Mermaid fences, <details> answer reveals, the `> **Predict first —**` callouts,
 * code blocks — passes through untouched. Nothing in this script writes to the source files.
 *
 * Run `npm run sync`; `npm run dev` and `npm run build` do it for you.
 */
import { readFile, writeFile, mkdir, rm, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../..');
const COURSE_DIR = 'networking-fundamentals';
const OUT = path.resolve(HERE, '../src/content/docs');

/** Base path when the site is served from a subdirectory (e.g. a GitHub Pages project site). */
const BASE = (process.env.BASE_PATH ?? '').replace(/\/+$/, '');
/**
 * Where a link that has no on-site page should point instead.
 *
 * A handful of targets are real files in the repository that are deliberately *not* pages: the audit,
 * `drills/lib.sh`, the drill scripts themselves. Left alone, those links reached the built HTML as
 * `href="../AUDIT.md"` — a relative path to a file the web server does not have, i.e. a 404 that looks
 * like a working link until it is clicked. The env var has been read here since the site was built,
 * but nothing ever set it, so the fallback never fired and thirteen links shipped dead.
 *
 * Deriving it from `origin` fixes that without asking whoever builds the site to know a flag, and it
 * stays correct in a fork, where a hardcoded URL would silently send every reader to someone else's
 * repository. An explicit SOURCE_REPO_URL still wins. Outside a git checkout, or with a non-GitHub
 * remote, the value is empty and those links are left exactly as they were — the previous behaviour.
 */
function sourceRepoUrl() {
  const fromEnv = (process.env.SOURCE_REPO_URL ?? '').replace(/\/+$/, '');
  if (fromEnv) return fromEnv;
  let remote;
  try {
    remote = execFileSync('git', ['remote', 'get-url', 'origin'], {
      cwd: REPO,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return '';
  }
  // git@github.com:owner/repo.git and https://github.com/owner/repo(.git) both land on the same URL.
  const m = remote.match(/^(?:git@github\.com:|https?:\/\/(?:[^@/]*@)?github\.com\/)(.+?)(?:\.git)?$/);
  return m ? `https://github.com/${m[1]}` : '';
}

const SOURCE_REPO_URL = sourceRepoUrl();

/**
 * When each source file was last committed, so every page can say when it was last true.
 *
 * A course this close to kernel behaviour invites exactly one question — "is this still current?" —
 * and nothing on the site answered it. Starlight's own `lastUpdated` cannot: it runs `git log` against
 * the *rendered* file, and everything in src/content/docs is generated and gitignored, so it would
 * find no history at all. The date has to be carried over from the source file here.
 *
 * One `git log` for the whole repo rather than one per file (70 process spawns for data that arrives in
 * a single pass). Output is newest-first, so the first time a path appears is its last change.
 *
 * Returns an empty map outside a git checkout — a tarball download still builds, it just has no dates.
 */
function lastCommitDates() {
  const dates = new Map();
  let out;
  try {
    out = execFileSync(
      'git',
      ['log', '--pretty=format:@%cI', '--name-only', '--diff-filter=AMR'],
      { cwd: REPO, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] },
    );
  } catch {
    return dates;
  }

  let current = null;
  for (const line of out.split('\n')) {
    if (line.startsWith('@')) current = line.slice(1);
    else if (line && current && !dates.has(line)) dates.set(line, current);
  }
  return dates;
}

const COMMIT_DATES = lastCommitDates();

/**
 * The `lastUpdated` value for a page, given its source path relative to the repo root.
 *
 * `false` — not a fallback to "now" — when a file has never been committed. A build timestamp on an
 * uncommitted draft would claim freshness the content has not earned, which is the opposite of what
 * this signal is for; Starlight omits the line entirely instead.
 */
function lastUpdatedFor(srcRel) {
  return COMMIT_DATES.get(srcRel) ?? false;
}

// -- Route table ---------------------------------------------------------------
// Acts keep their reading order; the URL drops the numeric filename prefix (which lives on in
// `sidebar.order` instead) so links stay readable and survive a lesson being renumbered.
const ACTS = [
  { srcDir: '00-orientation', slug: 'orientation' },
  { srcDir: 'act-1-one-machine', slug: 'act-1' },
  { srcDir: 'act-2-two-machines', slug: 'act-2' },
  { srcDir: 'act-3-the-internet', slug: 'act-3' },
  { srcDir: 'act-4-one-pretends-many', slug: 'act-4' },
  { srcDir: 'act-5-kubernetes', slug: 'act-5' },
  { srcDir: 'act-6-control-plane', slug: 'act-6' },
  { srcDir: 'act-7-workloads', slug: 'act-7' },
  { srcDir: 'act-8-trust', slug: 'act-8' },
  { srcDir: 'act-9-identity', slug: 'act-9' },
  { srcDir: 'act-10-cluster-security', slug: 'act-10' },
  { srcDir: 'act-11-observability', slug: 'act-11' },
];

/**
 * Pages authored directly in src/content/docs rather than projected from the course Markdown.
 * The sync clears everything else in that directory, so anything hand-written must be listed here
 * or it will be deleted on the next run. These are also the only entries tracked by git.
 */
const HAND_WRITTEN = new Set(['index.mdx', 'progress.mdx', 'history-map.mdx']);

/** Standalone pages: [source relative to repo root, destination relative to docs root, order]. */
const SINGLES = [
  [`${COURSE_DIR}/README.md`, 'course.md', 1],
  [`${COURSE_DIR}/the-whole-stack.md`, 'capstone/the-whole-stack.md', 1],
  [`${COURSE_DIR}/your-own-machine.md`, 'capstone/your-own-machine.md', 2],
  // The reference wing leads its own section. Its first two pages are the ones that make the rest
  // shrink: the map of where kernel state lives, and the naming grammar that lets a reader derive a
  // command instead of looking one up. The rest — the lab image, the code, the tool roster — follow.
  //
  // Four pages that used to sit in this list are deliberately not projected onto the site any more:
  // `05-per-act-commands.md`, `06-derive-it.md`, `drills/README.md` and `JOURNEY-MAP.md`/`Toolbelt.md`
  // (never listed by their own directory, so nothing to remove there). They still exist in the
  // repository — this is a lookup wing now, and a drill or a progress tracker wants the opposite of
  // what a lookup page wants. `reference/README.md` explains the split and still links to all four
  // for anyone who cloned the repo. Removing them from this list does not 404 the inbound links from
  // `diagnose.md` and the act READMEs: `rewriteLinks` sends anything with no route on the site to the
  // GitHub source instead.
  ['reference/README.md', 'reference/index.md', 1],
  ['reference/01-the-grammar.md', 'reference/the-grammar.md', 2],
  ['reference/03-the-map.md', 'reference/the-map.md', 3],
  ['reference/04-by-question.md', 'reference/by-question.md', 5],
  [`${COURSE_DIR}/code/README.md`, 'reference/build-the-lab-image.md', 8],
  // exam-prep is deliberately NOT a course act — it is rehearsal for a timed exam, which is the
  // banking the course refuses to do. It publishes under its own section so a reader can find it
  // without it ever appearing beside the lessons.
  ['exam-prep/README.md', 'exam-prep/index.md', 1],
  ['exam-prep/the-exam-path.md', 'exam-prep/the-exam-path.md', 2],
  ['exam-prep/cka-domain-map.md', 'exam-prep/cka-domain-map.md', 3],
  ['exam-prep/cks-domain-map.md', 'exam-prep/cks-domain-map.md', 4],
  ['exam-prep/kubectl-speed.md', 'exam-prep/kubectl-speed.md', 5],
  ['exam-prep/exam-day.md', 'exam-prep/exam-day.md', 6],
  ['exam-prep/authoring-sprint.md', 'exam-prep/authoring-sprint.md', 7],
];

/**
 * The four source files, projected verbatim onto one page at `/reference/the-code/`.
 *
 * This page exists because the course has two audiences and only one of them has the repo. The lessons
 * say things like "read `code/minihttp.c`" and show a *stripped* version of the server — fine if you
 * cloned, useless if you are reading the website, where the real file appeared nowhere at all. The
 * stripped version is also not the interesting one: minihttp.c's comments explain why every call is
 * there, which is a third of what Act I teaches.
 *
 * Generated rather than hand-written, for the same reason every lesson is: `networking-fundamentals/code`
 * stays the single source of truth, and a page copied by hand would drift the first time the server
 * gains a line. `lang` is what Shiki highlights the fence as.
 *
 * `minihttp.static` is deliberately absent — it is a checked-in aarch64 binary, not something to read.
 */
const CODE_FILES = [
  {
    src: `${COURSE_DIR}/code/minihttp.c`,
    lang: 'c',
    heading: 'minihttp.c',
    blurb:
      'The spine of the whole course: the ~40-line HTTP server you inspect in Act I, capture in Act III, '
      + 'run inside a namespace in Act IV and containerise in Act V. The comments are part of the lesson — '
      + 'they say why each call is there, not what it is called.',
  },
  {
    src: `${COURSE_DIR}/code/fd-demo.c`,
    lang: 'c',
    heading: 'fd-demo.c',
    blurb:
      'Opens a regular file and then a socket, and prints the descriptor it got for each. The whole point '
      + 'is the two numbers it prints, and that nothing in the program treats them differently.',
  },
  {
    src: `${COURSE_DIR}/code/Makefile`,
    lang: 'makefile',
    heading: 'Makefile',
    blurb: 'Builds both programs. Run inside the container — these are Linux binaries.',
  },
  {
    src: `${COURSE_DIR}/code/Dockerfile`,
    lang: 'dockerfile',
    heading: 'Dockerfile',
    blurb:
      'Builds `netlab`: netshoot\'s whole toolbox plus a C compiler, a real `lsof`, and `eza`. Its '
      + '`COPY . /code` is why building it needs the four files next to it in a directory.',
  },
];

/** Where `reference/the-code.md` is written, and the order it takes in the Reference sidebar. */
const CODE_PAGE = { dest: 'reference/the-code.md', order: 9 };

/** Supporting pages sort after the numbered lessons, in the order each act's README recommends. */
const SUPPORTING_ORDER = {
  'test-yourself.md': 900,
  'diagnose.md': 910,
  'in-the-wild.md': 930,
};

const SUPPORTING_LABELS = {
  'test-yourself.md': 'Test yourself',
  'diagnose.md': 'Diagnose it',
  'in-the-wild.md': 'In the wild',
};

/**
 * Sidebar labels where the authored H1 is a full sentence. Lesson titles are otherwise left exactly
 * as written — several are deliberately posed as a question rather than naming their answer, which is
 * the course's pedagogy, not an oversight to "fix".
 */
const LABEL_OVERRIDES = {
  [`${COURSE_DIR}/README.md`]: 'The reading path',
  // Its H1 is "The code, and running the lab on macOS", which was fine when it was the only page about
  // the code. Now that the sources themselves have a page, two sidebar rows both began "The code" — so
  // this one is labelled by the job it actually does.
  [`${COURSE_DIR}/code/README.md`]: 'Running the lab',
  [`${COURSE_DIR}/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md`]: 'TCP states & the SYN scan',
  [`${COURSE_DIR}/act-1-one-machine/06b-the-container-filesystem.md`]: "The container's filesystem",
  [`${COURSE_DIR}/act-5-kubernetes/06b-gateway-api.md`]: 'Gateway API',
};

// -- Helpers -------------------------------------------------------------------

/** `01-foo.md` -> 10, `01b-foo.md` -> 12, `09-foo.md` -> 90. Keeps b/c variants beside their parent. */
function orderFromFilename(name) {
  if (name === 'README.md') return 0;
  if (name in SUPPORTING_ORDER) return SUPPORTING_ORDER[name];
  const m = name.match(/^(\d+)([a-z])?-/);
  if (!m) return 500;
  return Number(m[1]) * 10 + (m[2] ? m[2].charCodeAt(0) - 96 : 0);
}

/** `05b-tcp-states-and-the-syn-scan.md` -> `tcp-states-and-the-syn-scan`. */
function slugFromFilename(name) {
  return name.replace(/\.md$/, '').replace(/^\d+[a-z]?-/, '');
}

/** Markdown inline formatting -> plain text, for frontmatter values Starlight renders as text. */
function plainText(md) {
  return md
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(?<![\w*])\*([^*\n]+)\*(?![\w*])/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncate(text, max = 158) {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const at = cut.lastIndexOf(' ');
  const kept = at > max * 0.6 ? cut.slice(0, at) : cut;
  return `${kept.replace(/[\s.,;:—-]+$/, '')}...`;
}

/**
 * Abbreviations whose full stop does not end a sentence. Without this, `summarise` would cut a
 * description at "e.g." and hand back half a clause.
 */
const ABBREV_RE = /(?:e\.g|i\.e|etc|vs|approx|cf|Dr|Mr|Ms|St|No|Fig)\.$/i;

/**
 * A page's meta description is what Google, a social card and Starlight's own search all show, so it
 * needs to be a complete thought. Truncating the opening paragraph at a fixed 158 characters gave us
 * 61 of 66 pages ending mid-clause — "the line for `/` — the one under your feet this whole act —
 * said something..." — which reads as broken rather than brief.
 *
 * So: keep whole sentences, adding them while the result still fits. Only when the very first
 * sentence is itself over the limit do we fall back to `truncate`'s word-boundary ellipsis, because
 * then there is no sentence boundary to stop at.
 *
 * Splitting on "sentence-final punctuation followed by whitespace" is safe for this corpus: a path
 * like `/proc/net/tcp` and a version like `1.1` have no space after the dot, so they survive intact.
 */
function summarise(text, max = 158) {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;

  const parts = trimmed.split(/(?<=[.?!])\s+/);
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    let piece = parts[i];
    while (ABBREV_RE.test(piece) && i + 1 < parts.length) piece += ` ${parts[++i]}`;
    const candidate = out ? `${out} ${piece}` : piece;
    if (candidate.length > max) break;
    out = candidate;
  }
  return out || truncate(trimmed, max);
}

/**
 * A sidebar label from the page title. Titles here often read `Topic — a clause explaining it`;
 * that clause is a subtitle, so drop it when the whole thing is too long to sit in a sidebar.
 */
function labelFromTitle(title) {
  let label = title.replace(/\s*\([^)]*\)\s*$/, '').trim();
  if (label.length > 32 && label.includes('—')) label = label.split('—')[0].trim();
  return label;
}

const MARK_RE = /@@X(\d+)@@/g;
const mark = (i) => `@@X${i}@@`;

/**
 * Replace fenced code blocks with opaque markers so nothing downstream can rewrite a shell command.
 * Line-based rather than one big regex, because the course also fences code *inside* blockquotes
 * (`> ```) — the fence line has a `>` prefix that a simple indent-anchored pattern would miss.
 */
function maskFences(text, stash = []) {
  const lines = text.split('\n');
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const open = lines[i].match(/^(?:\s*>)*\s*(`{3,}|~{3,})/);
    if (!open) {
      out.push(lines[i]);
      continue;
    }
    const fence = open[1];
    const closer = new RegExp(`^(?:\\s*>)*\\s*\\${fence[0]}{${fence.length},}\\s*$`);
    const buf = [lines[i++]];
    while (i < lines.length && !closer.test(lines[i])) buf.push(lines[i++]);
    if (i < lines.length) buf.push(lines[i]);
    stash.push(buf.join('\n'));
    out.push(mark(stash.length - 1));
  }
  return [out.join('\n'), stash];
}

/** Fenced blocks *and* inline code spans — every place a `](...)` must be left alone. */
function maskCode(text) {
  const [fenced, stash] = maskFences(text);
  const masked = fenced.replace(/`[^`\n]+`/g, (m) => {
    stash.push(m);
    return mark(stash.length - 1);
  });
  return [masked, stash];
}

function unmask(text, stash) {
  return text.replace(MARK_RE, (_, i) => stash[Number(i)]);
}

// -- Build the route table and the source -> URL map ---------------------------

/**
 * Generated reference wings: one page per tool, one per kernel interface. Listed as directories
 * rather than in SINGLES because there are eighty of them and they change whenever
 * `reference/capabilities.json` does — an explicit list would be a second place to forget.
 *
 * The *tool* pages are written by `tools/gen-tool-pages.py` and must never be hand-edited. The
 * `README.md`s are the hand-written half and become each directory's landing page: the roster at
 * `reference/tools/README.md`, and one per interface holding the grammar and path rules shared by
 * every tool speaking it — which is why none of that is repeated on the individual tool pages.
 *
 * The wing takes slot 4, which is where the roster used to sit as a standalone page. It is still
 * the page a reader wants fourth, and now the eighty it indexes hang underneath it.
 */
const REFERENCE_DIRS = [
  { srcDir: 'reference/tools', slug: 'reference/tools', order: 4 },
];

async function buildRoutes() {
  const routes = SINGLES.map(([src, dest, order]) => ({ src, dest, order, handOrdered: true }));

  for (const wing of REFERENCE_DIRS) {
    const dir = path.join(REPO, wing.srcDir);
    if (!existsSync(dir)) continue;
    // Recursive, because `reference/tools/` is one directory per kernel interface. That nesting is
    // the whole point: Starlight turns each directory into its own sidebar group, so the roster
    // arrives grouped by what a tool speaks without anyone maintaining a list of eighty entries.
    for (const rel of (await readdir(dir, { recursive: true })).sort()) {
      if (!rel.endsWith('.md')) continue;
      // A tool page is titled ``conntrack` — connection tracking`, which is right on the page and
      // noise in a sidebar of eighty siblings. The sidebar wants the name you would type, so take
      // the H1's first code span and let the expansion live on the page.
      const h1 = (await readFile(path.join(REPO, wing.srcDir, rel), 'utf8'))
        .match(/^#\s+`([^`]+)`/m);
      routes.push({
        src: `${wing.srcDir}/${rel}`,
        // A directory's README is its landing page, the same convention the acts use: `tools/
        // netlink/README.md` publishes at `/reference/tools/netlink/` rather than as a sibling
        // page called "README" that a reader would have to click past the group to reach.
        dest: `${wing.slug}/${rel.replace(/(^|\/)README\.md$/, '$1index.md')}`,
        // There is no reading order inside a group — you arrive at `conntrack` because you typed
        // it, not because `bridge` came first. Alphabetical is the honest default.
        order: wing.order,
        label: h1 ? h1[1] : undefined,
      });
    }
  }

  for (const act of ACTS) {
    const dir = path.join(REPO, COURSE_DIR, act.srcDir);
    const files = (await readdir(dir)).filter((f) => f.endsWith('.md')).sort();
    for (const name of files) {
      routes.push({
        src: `${COURSE_DIR}/${act.srcDir}/${name}`,
        dest: name === 'README.md'
          ? `${act.slug}/index.md`
          : `${act.slug}/${slugFromFilename(name)}.md`,
        order: orderFromFilename(name),
        // Inside an "Act I — ..." sidebar group, repeating the act's own long title is noise.
        label: name === 'README.md' && act.slug.startsWith('act-')
          ? 'Overview'
          : SUPPORTING_LABELS[name],
      });
    }
  }

  for (const r of routes) {
    if (!existsSync(path.join(REPO, r.src))) throw new Error(`route source missing: ${r.src}`);
    const clean = r.dest.replace(/\.md$/, '').replace(/(^|\/)index$/, '$1');
    r.url = `${BASE}/${clean}`.replace(/([^/])$/, '$1/');
  }

  const seen = new Map();
  for (const r of routes) {
    if (seen.has(r.url)) throw new Error(`URL collision at ${r.url}: ${seen.get(r.url)} + ${r.src}`);
    seen.set(r.url, r.src);
  }

  // Two pages in the same sidebar group claiming the same `order` do not error — Starlight silently
  // breaks the tie alphabetically, which is how `reference/the-code.md` and the drill index both sat
  // at 9 and happened to come out in the intended order by luck. Adding a page above either of them
  // would have reshuffled the group with nothing to say why. So: hand-written orders must be unique
  // within their group.
  //
  // Only `handOrdered` routes are checked. The eighty generated tool pages deliberately *share* one
  // order per group — there is no reading order inside a tool roster, and alphabetical is the point —
  // so a blanket check would fire on the one case where a tie is correct. CODE_PAGE is included by
  // adding its slot below, because it is hand-written even though it is assembled elsewhere.
  const slots = new Map([[`reference:${CODE_PAGE.order}`, CODE_PAGE.dest]]);
  for (const r of routes) {
    if (!r.handOrdered) continue;
    const key = `${path.posix.dirname(r.dest)}:${r.order}`;
    if (slots.has(key)) {
      throw new Error(`sidebar order ${r.order} claimed twice in ${path.posix.dirname(r.dest)}: ${slots.get(key)} + ${r.dest}`);
    }
    slots.set(key, r.dest);
  }

  return routes;
}

// -- Link rewriting ------------------------------------------------------------

function rewriteLinks(body, srcRel, urlMap, unresolved) {
  const [masked, stash] = maskCode(body);
  const srcDir = path.posix.dirname(srcRel);

  const rewritten = masked.replace(/\]\(([^)\s]+)\)/g, (whole, target) => {
    if (/^(https?:|mailto:|#|\/)/.test(target)) return whole;

    const hashAt = target.indexOf('#');
    const hash = hashAt === -1 ? '' : target.slice(hashAt);
    const filePart = hashAt === -1 ? target : target.slice(0, hashAt);
    if (!filePart) return whole; // same-page anchor

    const resolved = path.posix
      .normalize(path.posix.join(srcDir, filePart))
      .replace(/\/$/, '');

    // Illustrations are referenced *relatively* by the lessons (`../../illustrations/…`) so the image
    // still renders when the Markdown is read on GitHub. scripts/sync-illustrations.mjs copies the
    // same files into public/, so on the site that path becomes an absolute URL under BASE. Without
    // this the relative path would fall through to `unresolved` and 404 on every lesson page.
    if (resolved.startsWith('illustrations/')) return `](${BASE}/${resolved}${hash})`;

    const url = urlMap.get(resolved);
    if (url) return `](${url}${hash})`;

    unresolved.push({ from: srcRel, target });
    if (SOURCE_REPO_URL) return `](${SOURCE_REPO_URL}/blob/main/${resolved}${hash})`;
    return whole;
  });

  return unmask(rewritten, stash);
}

// -- Code fence languages ------------------------------------------------------

/**
 * The course writes almost every code block as a bare ``` fence, which Shiki renders as `plaintext`:
 * one flat colour, no highlighting. Tagging them all as `bash` would be worse than doing nothing,
 * because those fences are heterogeneous — roughly 56% are commands, and the rest are command
 * *output*, ASCII diagrams and fd listings.
 *
 * So this classifier is deliberately high-precision and low-recall: a fence becomes `bash` only when
 * every non-empty line is confidently a command. Anything uncertain stays plaintext. Leaving output
 * uncoloured is also the pedagogically correct default — this course teaches you to read raw kernel
 * output, and syntax colour would imply a structure that isn't there.
 *
 * The source files keep their bare fences; this only affects the generated site.
 */
const SHELL_COMMANDS = new Set(`
ip iptables ip6tables nft curl wget cat ls docker kubectl ping ping6 dig drill dog host
tcpdump ss netstat nc ncat socat conntrack arp arping ethtool bridge tc nsenter unshare mount findmnt
umount df stat ln rm mkdir touch echo printf export exec cd pwd sleep kill strace ltrace ps
bpftrace nmap python3 python make gcc cc bash sh sudo kind helm openssl base64 xxd od hexdump
awk sed grep cut sort uniq head tail wc tr tee seq watch dhclient resolvectl systemctl modprobe sysctl
traceroute mtr nslookup lsof prlimit ulimit chmod chown id whoami uname hostname date env true
eza bat fd rg jq yq cilium hubble crictl getent
iptables-save iptables-restore etcdctl etcdutl kubeadm runc capsh getpcaps apparmor_parser trivy cosign crane kube-bench falco kyverno
kustomize wg nstat bpftool devlink ipvsadm ipset scapy tracepath pkill timeout xargs readlink
ctr containerd skopeo umoci apk buildctl buildkitd
pwru retis tshark iperf3 pgrep ifconfig nettop scutil dscacheutil pfctl lsns
`.trim().split(/\s+/));

/** Box-drawing and arrow glyphs: a sure sign the block is a diagram, not a command. */
const BOX_DRAWING = /[─-╿▲▼◄►←-↓]/;

function looksLikeCommands(body) {
  const lines = body.split('\n').filter((l) => l.trim() !== '');
  if (lines.length === 0) return false;

  let sawCommand = false;
  for (const line of lines) {
    if (BOX_DRAWING.test(line)) return false;
    const s = line.trim();
    if (s.startsWith('#')) continue; // a comment is fine inside a command block
    if (/^([|=<*.]|\+-|--)/.test(s)) return false; // table rule, diff, prose punctuation
    const token = s.split(/\s+/)[0].replace(/^[$(]+/, '').replace(/[;|]+$/, '');
    if (SHELL_COMMANDS.has(token) || /^[A-Za-z_][A-Za-z0-9_]*=\S*$/.test(token)) {
      sawCommand = true;
      continue;
    }
    return false;
  }
  return sawCommand;
}

/** Rewrite bare opening fences to ```bash where the body classifies as commands. */
function tagCodeFences(body) {
  const lines = body.split('\n');
  const out = [];

  for (let i = 0; i < lines.length; i++) {
    // Allow a blockquote prefix: the course fences commands inside `>` callouts too.
    const open = lines[i].match(/^((?:\s*>)*\s*)(`{3,}|~{3,})[ \t]*([A-Za-z0-9_+-]*)[ \t]*$/);
    if (!open) {
      out.push(lines[i]);
      continue;
    }

    const [, prefix, fence, lang] = open;
    const closer = new RegExp(`^(?:\\s*>)*\\s*\\${fence[0]}{${fence.length},}\\s*$`);
    const openLine = lines[i];
    const buf = [];
    i++;
    while (i < lines.length && !closer.test(lines[i])) buf.push(lines[i++]);
    const closeLine = i < lines.length ? lines[i] : null;

    // Strip any blockquote prefix before classifying the body.
    const stripped = buf.map((l) => l.replace(/^(\s*>)+\s?/, '')).join('\n');
    const tag = !lang && looksLikeCommands(stripped) ? 'bash' : lang;

    out.push(tag && !lang ? `${prefix}${fence}${tag}` : openLine, ...buf);
    if (closeLine !== null) out.push(closeLine);
  }

  return out.join('\n');
}

// -- Callouts ------------------------------------------------------------------

/**
 * The course carries its pedagogy in a handful of recurring blockquotes — `> **Predict first —**`
 * before an experiment, `> **Ticket:**` opening an on-call drill, and so on. On GitHub they all render
 * as the same grey bar. Here each kind gets its own colour and icon, so a reader can see at a glance
 * that they are being asked to commit to a prediction rather than just read on.
 *
 * The blockquote is wrapped in a div rather than converted to anything else: CommonMark parses
 * Markdown inside an HTML block as long as blank lines separate them, so every link, code fence and
 * emphasis inside the quote still works, and the source stays untouched.
 */
const CALLOUT_KINDS = [
  [/^predict/i, 'predict'],
  // Two spellings of the same device: `Check yourself` mid-lesson, `Question N` on a test-yourself
  // page, where the numbering is the point and a generic lead would read oddly six times in a row.
  [/^check yourself|^question \d+/i, 'checkpoint'],
  [/^you understand this when you can/i, 'mastery'],
  [/^ticket\b/i, 'ticket'],
  [/^on your own machine/i, 'machine'],
  [/^where\b|^where you type this/i, 'where'],
  [/^the file\b/i, 'file'],
  [/^(this is a )?side ?road/i, 'sidenote'],
];

function classifyCallout(label) {
  for (const [re, kind] of CALLOUT_KINDS) if (re.test(label)) return kind;
  return null;
}

function tagCallouts(body) {
  const lines = body.split('\n');
  const out = [];

  for (let i = 0; i < lines.length; i++) {
    if (!/^\s*>/.test(lines[i])) {
      out.push(lines[i]);
      continue;
    }

    const start = i;
    while (i + 1 < lines.length && /^\s*>/.test(lines[i + 1])) i++;
    const quote = lines.slice(start, i + 1);

    const lead = quote[0].match(/^\s*>\s*\*\*(.+?)\*\*/);
    const kind = lead ? classifyCallout(lead[1].trim()) : null;

    if (!kind) {
      out.push(...quote);
      continue;
    }

    // Predictions and checkpoints get a custom element rather than a div, so Predict.astro and
    // Checkpoint.astro can add the interaction. Same classes either way, so with JavaScript off they
    // are the callouts they always were.
    const tag = kind === 'predict' ? 'kz-predict' : kind === 'checkpoint' ? 'kz-checkpoint' : 'div';

    // A checkpoint's answer is the `<details>` block written after the question, so the element has to
    // reach past the blockquote to take it in — otherwise the reveal ends up a sibling of the callout
    // and the self-grade row has nothing to attach to.
    const extra = [];
    if (kind === 'checkpoint') {
      let j = i + 1;
      while (j < lines.length && lines[j].trim() === '') j++;
      if (lines[j]?.trim().startsWith('<details')) {
        while (j < lines.length && !lines[j].trim().startsWith('</details>')) extra.push(lines[j++]);
        if (j < lines.length) {
          extra.push(lines[j]);
          i = j;
        } else {
          throw new Error('checkpoint: unterminated <details> after a "Check yourself" callout');
        }
      }
    }

    out.push(
      `<${tag} class="callout callout--${kind}">`,
      '',
      ...quote,
      ...(extra.length ? ['', ...extra] : []),
      '',
      `</${tag}>`,
    );
  }

  return out.join('\n');
}

// -- Answer-first lines --------------------------------------------------------

/** A paragraph that is nothing but one bold sentence — the shape of an answer-first line. */
const ANSWER_RE = /^\*\*[^*\s].*\*\*$/;

/**
 * Give the answer-first line under a question heading its own visual treatment.
 *
 * Nearly every heading in this course is a *question*, which is the right way to open a section and
 * the wrong way to end up skimmable: the answer used to be somewhere inside the 150-word block
 * underneath, so a reader scanning the page got a list of questions and no answers. The lessons now
 * lead each section with a single bold sentence that answers its own heading, and this wraps that
 * sentence so it reads as a distinct kind of thing rather than just some bold text.
 *
 * On GitHub it stays a bold sentence, which is exactly right there — the source is untouched.
 *
 * Deliberately narrow: an H2–H4, then (past any blank lines) a *single* line that is entirely bold
 * and ends its paragraph. A bold lead-in to a longer paragraph — `**Predict first —** write down…` —
 * fails the "entirely bold" test, and a bold run inside a paragraph never starts one.
 */
function tagAnswers(body) {
  const lines = body.split('\n');
  const out = [];
  let fence = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const f = line.match(/^\s*(`{3,}|~{3,})/);

    // Track fences so a `# comment` inside a shell block is never read as a heading.
    if (fence) {
      out.push(line);
      if (f && f[1][0] === fence[0] && f[1].length >= fence.length) fence = null;
      continue;
    }
    out.push(line);
    if (f) {
      fence = f[1];
      continue;
    }
    if (!/^#{2,4}\s/.test(line)) continue;

    let j = i + 1;
    while (j < lines.length && lines[j].trim() === '') j++;
    if (j >= lines.length) continue;

    const candidate = lines[j].trim();
    const endsParagraph = j + 1 >= lines.length || lines[j + 1].trim() === '';
    if (!endsParagraph || !ANSWER_RE.test(candidate)) continue;

    // Blank lines inside the wrapper so CommonMark still renders the links and code spans in it.
    out.push(...lines.slice(i + 1, j), '<div class="answer">', '', candidate, '', '</div>');
    i = j;
  }

  return out.join('\n');
}

// -- Lesson nav ----------------------------------------------------------------

// The footer nav line, in the several shapes the course actually writes it:
//   ← Prev: **[…](…)** · ↑ **[Act I overview](…)** · Next: **[…](…)** →
//   ← Back to **[Act I overview](README.md)** · Next: **[Diagnose it →](…)**, then **[Act II →](…)**
//   → Next: **[…](…)**                          (the orientation lessons, which have no prev arm)
const NAV_LINE_RE = /^(?:←|↑|→|Next:)/;

/**
 * Reshape or remove the footer nav line.
 *
 * On GitHub that line is exactly right: one line of plain text under a rule, and the only navigation
 * a file in a repo has. On the site it is mostly redundant — Starlight's `pagination: true` renders
 * prev/next cards immediately below it, and 75 of the 127 links across these lines point at exactly
 * the page one of those cards already points at. Stacking the line would have made a third copy.
 *
 * So where the section has an overview page, the whole block goes: prev/next are the cards' job, and
 * the one arm the cards never provide — the link up to the act overview — is now the page-title
 * eyebrow (`PageTitle.astro`), which is a better home for it anyway. Where the section has *no*
 * overview page there is no eyebrow link to inherit that job, so the line stays and is stacked one
 * destination per row: at a narrow width the interpuncts stop separating anything once a row wraps,
 * and three destinations read as one run-on sentence.
 *
 * The trailing `---` goes with it. It exists only to fence the nav off from the prose, so leaving it
 * behind would end every page on a dangling rule.
 *
 * Detection is deliberately narrow — the last non-empty line, starting with the course's own arrow or
 * `Next:`, and containing a link — so an ordinary paragraph is never caught. The source is untouched;
 * this only reshapes the projection.
 */
function tagLessonNav(body, dest, sectionsWithOverview) {
  const lines = body.split('\n');

  let last = lines.length - 1;
  while (last >= 0 && lines[last].trim() === '') last--;
  if (last < 0) return body;

  const line = lines[last].trim();
  if (!NAV_LINE_RE.test(line) || !line.includes('](')) return body;

  // Drop the rule that fences the nav off, and any blank lines between the two.
  let cut = last - 1;
  while (cut >= 0 && lines[cut].trim() === '') cut--;
  if (cut >= 0 && /^-{3,}$/.test(lines[cut].trim())) cut--;
  else cut = last - 1;

  const before = lines.slice(0, cut + 1);
  const after = lines.slice(last + 1);

  if (sectionsWithOverview.has(dest.split('/')[0])) return [...before, ...after].join('\n');

  const arms = line.split(/\s+·\s+/).map((a) => a.trim()).filter(Boolean);
  const block = [
    '',
    '<nav class="lesson-nav" aria-label="Lesson navigation">',
    '',
    // Blank lines around each arm so Markdown still renders it — the arms carry links and bold.
    ...arms.flatMap((a) => [a, '']),
    '</nav>',
  ];

  return [...before, ...block, ...after].join('\n');
}

// -- Figures -------------------------------------------------------------------

const FIGURE_RE = /^\s*<!--\s*figure(?::\s*([a-z0-9-]+))?\s*-->\s*$/i;
const ANNOTATE_RE = /^\s*<!--\s*annotate:\s*([a-z0-9-]+)\s*-->\s*$/i;

/**
 * `<!-- scrollytell -->` marks a page whose numbered stages should get a sticky descent tracker.
 *
 * Unlike the figure and annotate directives it annotates nothing beneath it — the element finds the
 * stages in the rendered DOM (see Scrollytell.astro) — so it is a standalone line rather than a fence
 * marker. GitHub hides it, as with the others.
 */
const SCROLLY_RE = /^\s*<!--\s*scrollytell\s*-->\s*$/i;

/**
 * Upgrade a fenced ASCII diagram that a lesson has marked as a figure.
 *
 *   <!-- figure: tcp-handshake -->   ->  an animated <kz-diagram> built from that named spec
 *   <!-- figure -->                  ->  a framed diagram, ASCII left exactly as written
 *
 * The directive is an HTML comment on purpose: GitHub hides it and renders the ASCII underneath
 * unchanged, so the course Markdown stays the single source of truth and `check_pedagogy.py` sees
 * the same file it always did. Nothing about the diagram moves into this script — the ASCII stays
 * in the output as the element's own child and becomes its no-JS fallback.
 *
 * Why bother at all: outside Acts I and II the course carries its diagrams as ASCII inside bare
 * fences, which Shiki renders as flat monospace — visually identical to the command *output* blocks
 * either side of it. A reader can't tell a picture of the handshake from a paste of what tcpdump
 * printed. Framing them as figures is the fix; animating the few that are really about *ordering in
 * time* is the bonus.
 */
function tagFigures(body, srcRel) {
  const lines = body.split('\n');
  const out = [];

  for (let i = 0; i < lines.length; i++) {
    if (SCROLLY_RE.test(lines[i])) {
      out.push('<kz-scrollytell></kz-scrollytell>');
      continue;
    }

    const annotate = lines[i].match(ANNOTATE_RE);
    const directive = annotate ?? lines[i].match(FIGURE_RE);
    if (!directive) {
      out.push(lines[i]);
      continue;
    }
    const spec = directive[1] ?? null;

    // The fence being annotated, past any blank lines the author left between the two.
    let j = i + 1;
    while (j < lines.length && lines[j].trim() === '') j++;
    const open = lines[j]?.match(/^\s*(`{3,}|~{3,})/);
    if (!open) {
      throw new Error(`${srcRel}: <!-- figure --> is not followed by a fenced block`);
    }

    const fence = open[1];
    const closer = new RegExp(`^\\s*\\${fence[0]}{${fence.length},}\\s*$`);
    const block = [lines[j++]];
    while (j < lines.length && !closer.test(lines[j])) block.push(lines[j++]);
    if (j >= lines.length) {
      throw new Error(`${srcRel}: unterminated fence after <!-- figure -->`);
    }
    block.push(lines[j]);

    // Blank lines around the fence so CommonMark still parses it as Markdown inside the HTML block.
    const [openTag, closeTag] = annotate
      ? [`<kz-annotate class="kz-figure" spec="${spec}">`, '</kz-annotate>']
      : spec
        ? [`<kz-diagram class="kz-figure" spec="${spec}">`, '</kz-diagram>']
        : ['<div class="kz-figure">', '</div>'];
    out.push(openTag, '', ...block, '', closeTag);
    i = j;
  }

  return out.join('\n');
}

// -- Lesson metering ----------------------------------------------------------

/**
 * Measure a lesson so the page can tell the reader what it is asking of them before they start.
 *
 * Computed here rather than in a component because this is the only place that sees the Markdown as
 * text: by the time Starlight renders a page, the body is a compiled component and counting its words
 * would mean re-parsing what this script already has in a string.
 *
 * `commands` counts fenced blocks the classifier tagged `bash` — so it is a count of *blocks to run*,
 * not lines, which is the number that predicts how long a lesson actually takes. Output blocks and
 * ASCII diagrams are excluded, which is exactly why `tagCodeFences` is deliberately high-precision.
 */
function meterLesson(content) {
  const [masked, stash] = maskFences(content);

  // 180 wpm, not the usual 200–250: this is dense technical prose with hex to decode in it, and an
  // estimate that flatters the reader is worse than no estimate at all.
  const words = masked
    .replace(MARK_RE, ' ')
    .replace(/<\/?[a-z][^>]*>/gi, ' ')
    .split(/\s+/)
    .filter(Boolean).length;
  const minutes = Math.max(1, Math.round(words / 180));

  const commands = stash.filter((block) => /^(?:\s*>)*\s*`{3,}bash\b/.test(block)).length;

  // "Needs the lab" means the reader has to have a container running before the page is useful, which
  // the lessons signal by spelling out a `docker run` line or by driving a cluster with kubectl.
  const needsLab = /docker run|docker exec|kubectl |kind create/.test(content);

  return { minutes, commands, needsLab };
}

// -- Page generation ----------------------------------------------------------

function parsePage(raw, srcRel) {
  if (raw.includes('@@X')) throw new Error(`${srcRel}: source contains the reserved marker @@X`);

  const lines = raw.split('\n');
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;

  // `<!-- site:cut -->` ends the published page. JOURNEY-MAP.md is both the reader-facing map and the
  // authoring doc for whoever writes the next stage; the planning half (tool-selection reasoning, build
  // order, open questions) belongs in the repo but not in front of someone who came to see the
  // destination. The marker keeps one source of truth without publishing the backlog.
  const cutAt = lines.findIndex((l) => /^\s*<!--\s*site:cut\s*-->\s*$/i.test(l));
  if (cutAt !== -1) lines.length = cutAt;

  let title = null;
  if (lines[i]?.startsWith('# ')) {
    title = plainText(lines[i].slice(2));
    lines.splice(i, 1);
    while (lines[i]?.trim() === '') lines.splice(i, 1);
  }

  // Description: the first ordinary paragraph. Skip blockquote callouts, tables, lists, headings,
  // code and raw HTML — those are structure, not a summary. Inline code is fine; plainText strips
  // the backticks.
  let description = '';
  const [maskedForDesc] = maskFences(lines.join('\n'));
  // A folded answer is an ordinary paragraph as far as this scan is concerned, and on the
  // test-yourself pages it is the *first* one — so without this the page's own meta description
  // would give away question 1. Drop every `<details>` region before looking.
  const blocks = maskedForDesc
    .replace(/<details>[\s\S]*?<\/details>/gi, '')
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);
  for (const block of blocks) {
    if (/^([<>|#*!-]|\d+\.|@@X)/.test(block) || NAV_LINE_RE.test(block)) continue;
    description = summarise(plainText(block));
    break;
  }
  // A page that is nothing but questions and their folded answers (test-yourself) has no ordinary
  // paragraph at all, and falling through left it describing itself as "<details> <summary>Answer".
  // Its opening blockquote is the page's own instructions, which is exactly the summary we want.
  if (!description) {
    const quote = blocks.find((b) => b.startsWith('>'));
    if (quote) description = summarise(plainText(quote.replace(/^\s*>\s?/gm, '')));
  }

  return { title, description, body: lines.join('\n').trim() };
}

/**
 * Starlight's prev/next cards follow *sidebar order*, which is not always the authored reading path.
 * Act I is the clear case: its climax (`06-everything-is-a-file.md`) hands the reader straight to
 * `test-yourself.md`, but sidebar order puts the explicitly-optional `06b-the-container-filesystem.md`
 * next — so the site spliced a side-road into the main path and dropped the recall page the lesson's
 * own closing sentence was pointing at.
 *
 * The author already states the intended path, on the footer nav line that `tagLessonNav` strips. So
 * read it here, before it goes, and hand it to Starlight as explicit `prev`/`next` frontmatter. The
 * `↑` arm is ignored: linking up to the act overview is the page-title eyebrow's job.
 */
function paginationFromNav(body, srcRel, urlMap) {
  const lines = body.split('\n');
  let last = lines.length - 1;
  while (last >= 0 && lines[last].trim() === '') last--;
  if (last < 0) return {};

  const line = lines[last].trim();
  if (!NAV_LINE_RE.test(line) || !line.includes('](')) return {};

  const srcDir = path.posix.dirname(srcRel);
  const found = {};
  for (const raw of line.split(/\s+·\s+/)) {
    const arm = raw.trim();
    let dir = null;
    if (arm.startsWith('←')) dir = 'prev';
    else if (/(?:^|\s)Next:/.test(arm) || arm.endsWith('→')) dir = 'next';
    if (!dir || found[dir]) continue;

    const m = arm.match(/\[([^\]]+)\]\(([^)\s#]+)(?:#[^)]*)?\)/);
    if (!m) continue;
    const url = urlMap.get(path.posix.normalize(path.posix.join(srcDir, m[2])));
    if (url) found[dir] = { link: url, label: plainText(m[1]) };
  }
  return found;
}

/**
 * A heading's anchor, matching `github-slugger` — which is what Starlight generates heading ids with.
 *
 * The one rule worth stating, because getting it wrong is silent: punctuation is *deleted*, hyphens are
 * *kept*. So `fd-demo.c` is `fd-democ`, not `fddemoc`. A near-miss here does not 404 — the link just
 * quietly lands at the top of the page instead of at the file, on every reference in Act I.
 */
function slugify(heading) {
  return heading
    .toLowerCase()
    .replace(/[^a-z0-9 -]/g, '')
    .replace(/ +/g, '-');
}

/**
 * Build `/reference/the-code/` — every source file the course carries, in full.
 *
 * The opening section is the part that matters for a website-only reader: the lab image is built with
 * `docker build -t netlab networking-fundamentals/code`, which needs a build *context*, so someone who
 * never clones cannot run that command. Copying four files into a directory is the whole workaround,
 * and it belongs next to the files being copied.
 *
 * Any link written here must be a finished site URL. This body is assembled directly and never passes
 * through `rewriteLinks`, so a relative `README.md` would resolve against `/reference/` and 404.
 */
async function buildCodePage(lastUpdated) {
  const parts = [];

  parts.push(
    'Every file the course compiles, in full. The lessons quote fragments of these where a fragment is'
      + ' the point; this is the whole of it, so nothing in the course refers to code you cannot see.',
    '',
    '## Reading on the web? You need one folder, once',
    '',
    'The course asks you to clone it, but almost nothing actually depends on that. The lab image bakes'
      + ' these sources in at `/code`, and every command in Acts I–IV runs *inside* the container against'
      + ' that path — so the only step that ever names a folder on your Mac is the `docker build` that'
      + ' creates the image. Do that once from a folder you made yourself and you are done:',
    '',
    '```bash',
    'mkdir netlab && cd netlab',
    '# save all four files below into this folder, then:',
    'docker build -t netlab .',
    '```',
    '',
    '```bash',
    'ls               # minihttp.c  fd-demo.c  Makefile  Dockerfile',
    'docker images    # netlab      <- the only artefact that matters from here on',
    '```',
    '',
    '**After that, the folder has done its job.** The sources live inside the image, so no later lesson'
      + ' reads your filesystem: there is no working directory to be in and no path to keep track of. Keep'
      + ' the folder only if you want to *edit* the server later and mount your copy over `/code` — an'
      + ` optional detour described in [running the lab](${BASE}/reference/build-the-lab-image/), and not`
      + ' something any lesson asks for.',
    '',
    '### The three things worth knowing',
    '',
    '1. **Copy the `Makefile` with its tab intact.** `make` fails on spaces with the famously unhelpful'
      + ' *"missing separator"*. The copy button on the block below preserves it; a manual retype may not.',
    '2. **`docker build -t netlab .`** — the `.` is the folder holding the `Dockerfile`, which is why the'
      + ' course writes `networking-fundamentals/code` instead when you have cloned. Same image either'
      + ' way. Wherever the course shows the cloned form — the orientation, Act I lesson 1 — the `.` form'
      + ' is shown beside it.',
    '3. **You never compile on macOS.** These are Linux programs reading Linux `/proc`. `cc` runs inside'
      + ' the container, against `/code`.',
    '',
    '> **On your own machine —** you *can* build minihttp natively (`cc -Wall -o minihttp minihttp.c &&'
      + ' ./minihttp 8080`) and curl it, because sockets are POSIX. What you cannot do is the rest of Act'
      + " I: `/proc/net/tcp`, `/proc/<pid>/fd` and the fd table simply don't exist on macOS. That absence"
      + ' is the reason the container is here at all — worth confirming yourself, since it makes the point'
      + ' better than being told.',
    '',
    '### Act V needs nothing from here',
    '',
    'Act V swaps the container for a real Kubernetes cluster built by `kind`. Its manifests come from one'
      + ' of two places, and neither is this repository: the cluster config, Deployments, Services and'
      + ' NetworkPolicies are written out by the lesson that needs them with a `cat > file <<EOF` you run'
      + ' wherever you are standing, and the three big third-party installs — Flannel, Calico and'
      + ' ingress-nginx — are `kubectl apply -f <upstream URL>`. So the folder above is an Acts I–IV'
      + ' concern only.',
    '',
  );

  for (const file of CODE_FILES) {
    const source = await readFile(path.join(REPO, file.src), 'utf8');
    parts.push(
      `## ${file.heading}`,
      '',
      file.blurb,
      '',
      '```' + file.lang,
      source.replace(/\n+$/, ''),
      '```',
      '',
    );
  }

  const body = parts.join('\n');
  const fm = frontmatter({
    title: 'The code, in full',
    description:
      'Every source file the course compiles — minihttp.c, fd-demo.c, the Makefile and the Dockerfile —'
      + ' with a way to build the lab image without cloning the repository.',
    order: CODE_PAGE.order,
    label: 'The source code',
    lastUpdated,
  });

  const out = path.join(OUT, CODE_PAGE.dest);
  await mkdir(path.dirname(out), { recursive: true });
  await writeFile(out, `${fm}${body}`);
}

function frontmatter({ title, description, order, label, prev, next, lastUpdated }) {
  const out = ['---', `title: ${JSON.stringify(title)}`];
  if (description) out.push(`description: ${JSON.stringify(description)}`);
  // Always emitted, including as `false`: with the global option on, leaving it unset makes Starlight
  // fall back to `git log` on the generated file, which has no history and logs a warning per page.
  //
  // Unquoted, because Starlight's schema is `z.union([z.date(), z.boolean()])` and only a bare ISO 8601
  // scalar is parsed by YAML as a timestamp — quoting it yields a string and fails the union.
  out.push(`lastUpdated: ${lastUpdated === false ? 'false' : lastUpdated}`);
  out.push('sidebar:', `  order: ${order}`);
  if (label && label !== title) out.push(`  label: ${JSON.stringify(label)}`);
  for (const [key, arm] of [['prev', prev], ['next', next]]) {
    if (!arm) continue;
    out.push(`${key}:`, `  link: ${JSON.stringify(arm.link)}`, `  label: ${JSON.stringify(arm.label)}`);
  }
  out.push('---', '');
  return out.join('\n');
}

// -- Main ---------------------------------------------------------------------

async function main() {
  const routes = await buildRoutes();

  const urlMap = new Map(routes.map((r) => [r.src, r.url]));
  // The repo README links at the course folder itself rather than a file inside it.
  urlMap.set(COURSE_DIR, urlMap.get(`${COURSE_DIR}/README.md`));

  /* The .c/Makefile/Dockerfile sources are not pages, but lessons link to them — and on the site those
     links have somewhere real to go now. Each resolves to its own heading on the generated code page, so
     `[code/minihttp.c](../code/minihttp.c)` opens the actual file on GitHub and the right section of
     /reference/the-code/ on the web. Anchors match github-slugger, which is what Starlight uses. */
  const codeUrl = `${BASE}/${CODE_PAGE.dest.replace(/\.md$/, '')}/`;
  for (const file of CODE_FILES) {
    urlMap.set(file.src, `${codeUrl}#${slugify(file.heading)}`);
  }
  urlMap.set(`${COURSE_DIR}/code`, codeUrl);

  // Clear previously generated pages, but never the hand-written ones.
  if (existsSync(OUT)) {
    for (const entry of await readdir(OUT, { withFileTypes: true })) {
      if (HAND_WRITTEN.has(entry.name)) continue;
      await rm(path.join(OUT, entry.name), { recursive: true, force: true });
    }
  }

  // Which top-level sections have an overview page — i.e. whose page-title eyebrow can carry the
  // "up" link, which is what lets the footer nav block be dropped. Derived from the routes rather
  // than listed, so adding or removing a section README doesn't leave this behind.
  const sectionsWithOverview = new Set(
    routes.filter((r) => path.basename(r.dest) === 'index.md').map((r) => r.dest.split('/')[0]),
  );

  const unresolved = [];
  const meta = {};
  for (const r of routes) {
    const raw = await readFile(path.join(REPO, r.src), 'utf8');
    const { title, description, body } = parsePage(raw, r.src);
    if (!title) throw new Error(`${r.src}: no H1 to use as the page title`);

    const label = LABEL_OVERRIDES[r.src] ?? r.label ?? labelFromTitle(title);
    const content = tagLessonNav(
      tagFigures(
        tagAnswers(tagCallouts(tagCodeFences(rewriteLinks(body, r.src, urlMap, unresolved)))),
        r.src,
      ),
      r.dest,
      sectionsWithOverview,
    );
    const pagination = paginationFromNav(body, r.src, urlMap);
    const out = `${frontmatter({
      title,
      description,
      order: r.order,
      label,
      lastUpdated: lastUpdatedFor(r.src),
      ...pagination,
    })}${content}\n`;
    meta[r.url] = meterLesson(content);

    const dest = path.join(OUT, r.dest);
    await mkdir(path.dirname(dest), { recursive: true });
    await writeFile(dest, out, 'utf8');
  }

  /* Dated by the most recently touched source file on it, so the page's "last updated" tracks the code
     it displays rather than the script that assembles it. */
  const codeDates = CODE_FILES.map((f) => lastUpdatedFor(f.src)).filter(Boolean).sort();
  await buildCodePage(codeDates.length ? codeDates[codeDates.length - 1] : false);

  // A generated module rather than frontmatter: adding fields to frontmatter would mean extending
  // Starlight's content schema, and these are derived values, not something an author sets.
  await writeFile(
    path.resolve(HERE, '../src/lib/lesson-meta.generated.json'),
    `${JSON.stringify(meta, null, 2)}\n`,
    'utf8',
  );

  console.log(`sync: wrote ${routes.length + 1} pages to src/content/docs/`);

  if (unresolved.length) {
    const shown = new Set();
    const dest = SOURCE_REPO_URL ? `sent to ${SOURCE_REPO_URL}/blob/main/` : 'LEFT DEAD';
    console.warn(`sync: ${unresolved.length} link(s) point outside the site, ${dest}:`);
    for (const u of unresolved) {
      const key = `${u.from} -> ${u.target}`;
      if (shown.has(key)) continue;
      shown.add(key);
      console.warn(`  ${key}`);
    }
    if (!SOURCE_REPO_URL) {
      console.warn('  No GitHub `origin` remote to fall back to: these ship as relative .md hrefs that 404.');
      console.warn('  Set SOURCE_REPO_URL=https://github.com/<you>/learn_networking to point them somewhere real.');
    }
    if (process.argv.includes('--strict')) process.exit(1);
  }
}

main().catch((err) => {
  console.error(`sync failed: ${err.message}`);
  process.exit(1);
});
