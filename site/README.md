# site/ — the course as a website

An [Astro](https://astro.build) + [Starlight](https://starlight.astro.build) build of the course in
`../networking-fundamentals/`. Search, sidebar navigation, rendered Mermaid diagrams, dark/light mode.

```
npm install
npm run dev      # http://localhost:4321
npm run build    # static site into dist/
```

> If `npm install` fails with `EPERM … _cacache`, your global npm cache has root-owned files from an
> old npm bug. Either `sudo chown -R $(id -u):$(id -g) ~/.npm` once, or run
> `npm_config_cache=/tmp/npm-cache npm install`.

## The one rule: the Markdown is the source of truth

Lessons are **only ever edited in `../networking-fundamentals/`**. They stay plain Markdown that reads
fine on GitHub and is still gated by `../tools/check_pedagogy.py`. Nothing in this directory edits them.

`scripts/sync-content.mjs` projects those files into `src/content/docs/` (which is `.gitignore`d, apart
from the hand-written landing page) and is run automatically by `npm run dev` and `npm run build`. It
adds only what Starlight needs:

| It does | Why |
|---|---|
| Frontmatter: `title` from the `# H1`, `description` from the opening paragraph | Starlight needs both; the description also becomes the `<meta>` tag |
| Removes the `# H1` from the body | Starlight renders `title` as the page `<h1>`; leaving it would print it twice |
| Rewrites relative links — `01-the-fd-table.md` → `/act-1/the-fd-table/` | The numeric prefix moves into `sidebar.order`, so URLs survive renumbering |
| `sidebar.order` from the filename (`01b-` → 12), supporting pages after lessons | Preserves each act's reading order without a hand-maintained list |
| Wraps the course's recurring blockquotes in `.callout--<kind>` divs | See below |

Mermaid fences, `<details>` answer reveals, code blocks and prose all pass through untouched.

A relative link with no page behind it is **sent to GitHub**, at a URL derived from the `origin` remote
(`SOURCE_REPO_URL` overrides it; a non-GitHub remote or no checkout disables the fallback). That matters
because some link targets are real repository files that are deliberately not pages — `AUDIT.md`,
`drills/lib.sh` — and for a long time the fallback existed but nothing set the variable, so thirteen
links reached the built HTML as `href="../AUDIT.md"`: a relative path to a file the web server does not
have, which is a 404 that looks like a working link until it is clicked. Every run still lists them, and
now says where they went; `node scripts/sync-content.mjs --strict` turns the list into a non-zero exit
for CI.

A document that lives **outside** `../networking-fundamentals/` gets no page unless it is in `SINGLES`.
That is how `exam-prep/authoring-sprint.md` and `drills/README.md` were both invisible on the site while
being linked from a dozen places. Hand-written `sidebar.order` values must also be unique within their
group — `buildRoutes` throws if two claim the same slot, because Starlight otherwise breaks the tie
alphabetically and the group silently reshuffles the next time a page is added above them. The eighty
generated tool pages are exempt and *do* share one order per group, which is why the check is scoped to
the hand-listed routes rather than all of them.

Adding a lesson needs no changes here — drop the file in the act directory with a numeric prefix and
re-run. It will not get a stack rail unless you also put it in `LAYER_BY_PATH` (`src/lib/layers.ts`),
which is a judgement call and deliberately not automatic.

Adding a whole **act** touches five places, and missing any of the last three is silent — the pages
build and read fine, they just lose their furniture:

| File | What it gives the act |
|---|---|
| `ACTS` in `scripts/sync-content.mjs` | the pages exist at all |
| a sidebar group in `astro.config.mjs` | somewhere to find them |
| `SECTIONS` in `src/lib/sections.ts` | the eyebrow above each title, and the "up" link to the act overview — without which `sync-content.mjs` also keeps the source's footer nav block, because it only drops it for sections that have an overview page here |
| a motif in `src/components/Motif.astro` | the drawn mark beside each title. This is the one entry you cannot forget *quietly*: `MOTIFS` is a `Record<MotifName, …>`, so once the act is in `SECTIONS` the build reads `MOTIFS[name].seconds` off `undefined` and dies on that act's first page |
| a card in `scripts/gen-og.mjs` **and** its id in `SECTION_CARDS` (`src/components/Head.astro`) | the act's own social preview instead of the generic one |

Acts VI–X shipped with only the first two for a while, and the failure was worse than a missing
ornament: those sixty-odd pages had **no way up at all**. `tagLessonNav` had already dropped each
source's footer nav line, because it decides from the routes (any section with an `index.md`) and not
from `sections.ts` — so the act overview was reachable only from the collapsed sidebar, and on a phone
not at all. Nothing about that is a build error. Hence the table.

## Hand-written pages (important)

`npm run sync` **deletes everything in `src/content/docs/` that it didn't generate.** Pages authored by
hand must be listed in `HAND_WRITTEN` in `scripts/sync-content.mjs` or they vanish on the next run.
Currently: `index.mdx` (landing page) and `progress.mdx`.

## Progress tracking

`src/lib/progress.ts` plus two components. A "mark this page as done" toggle sits above Starlight's
footer on every doc page (`components/Footer.astro` overrides Starlight's, prepends the toggle, then
defers to `<Default>` so the edit link, last-updated and prev/next pagination are untouched), and
`/progress/` shows per-act bars.

State is `localStorage` only — no account, no network, nothing to serve. Two deliberate choices:

- **Keyed on `location.pathname`, not Starlight entry ids.** The ids are a content-loader implementation
  detail that has changed shape between Starlight versions; the URL scheme is ours and is what
  `sync-content.mjs` guarantees. Per-act counting is then a prefix match.
- **Totals come from `getCollection('docs')` at build time**, so they can't drift from the real page
  count. Only completion counts are client-side.

## Code fence languages

The course writes nearly every code block as a bare ` ``` ` fence, which Shiki renders as `plaintext` —
one flat colour, no highlighting. Blanket-tagging them `bash` would be worse than nothing, because
those 356 fences are heterogeneous: about 56% are commands and the rest are command *output*, ASCII
diagrams and fd listings.

So `tagCodeFences()` in the sync script is a deliberately **high-precision, low-recall** classifier — a
fence becomes `bash` only when *every* non-empty line is confidently a command (first token in an
explicit allowlist, or `VAR=value`, or a `#` comment), and anything containing box-drawing glyphs or
starting with table/prose punctuation is rejected outright. Current split: **206 bash, 161 plaintext,
5 c, 2 python**, with zero diagram or output blocks mislabelled.

Leaving output uncoloured is also the pedagogically correct default: this course teaches you to read raw
kernel output, and syntax colour would imply a structure that isn't there.

The source files keep their bare fences — this only affects the generated site. To highlight a block the
classifier misses, tag it explicitly in the source (` ```bash `) and the classifier leaves it alone.

## Code blocks — one rule

**Never override Expressive Code's `codeBackground` on its own, and don't pass a single theme.**
Starlight drives EC with a *pair* of themes (dark first, light second) and gates each behind the
`data-theme` value it sets on `<html>` — only ever `dark` or `light`. Passing one theme made EC emit
selectors keyed on `data-theme='github-dark'`, which never match, so its themed CSS never activated and
code text fell back to `inherit`; combined with a forced background that produced dark text on a
near-black surface — unreadable blocks with no visible frame or copy button. Background and foreground
come from the same theme and have to move together. `expressiveCode.styleOverrides` in
`astro.config.mjs` is therefore limited to geometry and type.

## Callouts

The course carries its pedagogy in a few recurring blockquotes. On GitHub they all render as the same
grey bar; here each gets a colour and an icon, so "commit to a prediction before you run this" is
visually distinct from "here is where you type it":

| Source blockquote | Renders as |
|---|---|
| `> **Predict first —** …` | violet, lightbulb — 44 of these |
| `> **You understand this when you can** …` | emerald, check |
| `> **Ticket:** …` | amber, ticket (the on-call drills) |
| `> **On your own machine —** …` | blue, laptop |
| `> **Where:** …` | indigo, pin |
| `> **The file:** …` | slate, document |
| `> **Side road —** …` | fuchsia, branch |

The blockquote is wrapped in a `<div>` rather than converted into anything else — CommonMark parses
Markdown inside an HTML block when blank lines separate them, so every link and code fence inside the
quote still works and the source file keeps its plain-Markdown meaning.

## Theming — the Kaluza design system

Two files:

- **`src/styles/tokens.css`** — the Kaluza brand design system, ported verbatim from the Claude Design
  mockup (`_ds/kaluza-brand-design-system-*/colors_and_type.css`): the Terra/Glacier/Sand/Claystone
  palette, the Aspekta type scale, the 8px spacing grid, radii, shadows and motion. Additions beyond
  the original are individually marked `ADDED` with the reason (all of them are either dark-mode
  counterparts, which the light-only mockup had no need for, or contrast-driven extra ramp steps).
- **`src/styles/global.css`** — maps those tokens onto Starlight and styles every component.

Starlight's convention is `:root` = dark, `[data-theme='light']` = light. **The light theme is the
faithful port of the mockup**; the dark theme is derived from the design system's own `--bg-dark` /
`--fg-on-dark` tokens and is an extrapolation, not something the mockup specified.

Colour overrides are declared **unlayered** so they beat `@astrojs/starlight-tailwind`'s ramp-position
derivations (which live in `@layer utilities`) — the accent needs exact values to clear WCAG AA, not
whatever a ramp index happens to produce. Measured ratios are recorded in a comment above the block.

Two Starlight internals are overridden deliberately, both noted in the CSS:

- `.hero` is forced to one column. Above 50rem Starlight sets `grid-template-columns: 7fr 4fr` to seat
  a hero image beside the copy; with no image that squeezed the copy into 7/11 of the width and pulled
  it off centre.
- Hero buttons are `.sl-link-button`, **not** the older `.action` class.

Neither needs `!important`: this file is unlayered, Starlight's are in `@layer starlight.*`, and its
`:where()`-scoped selectors add no specificity.

Fonts ship as four Aspekta weights (400/500/600/750) from `src/styles/fonts/`, referenced with relative
URLs so Vite hashes them and `base` is handled. They're TTF as supplied — converting to WOFF2 would cut
~228 KB to roughly a third if that matters.

**daisyUI is no longer used anywhere.** The plugin line stays only because removing it is your call; it
tree-shakes to zero bytes now. If you drop it, keep in mind why `prefix: dz-` is there: unprefixed,
daisyUI's `.hero`, `.stack`, `.card`, `.dropdown` and `.toggle` collide with Starlight's own class
names and win on layer order — `.stack` in particular overlaps all its children in one grid cell.

### Branding

The tokens (palette, type, spacing) are in use. The **Kaluza logo and lockup from the mockup are
deliberately not** — a personal learning site carrying them could read as an official Kaluza
publication. `assets/kaluza-icon-black.svg` is in the archive if you decide you want the footer mark.

## Deploying

The output is a static directory, so any host works. For a subpath deploy (a GitHub Pages project site,
for instance) set both variables — the sync script reads `BASE_PATH` too, so generated links get the
same prefix:

```
SITE_URL=https://you.github.io BASE_PATH=/learn_networking npm run build
```

Set `SOURCE_REPO_URL=https://github.com/<you>/learn_networking` to point links that have no page on the
site (`../../tools/README.md`, the C sources) at GitHub instead of leaving them relative.
