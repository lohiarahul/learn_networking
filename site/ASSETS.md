# Third-party visual assets

Every image asset vendored into this site, where it came from, and what its licence requires. Nothing
here is fetched at runtime — the site has no external asset hosts, by design.

## Kubernetes icons

**Files:** `public/icons/k8s/{pod,svc,ing,node}.svg` — `pod`, `svc` and `ing` are in use;
`node.svg` is vendored but not yet referenced by any spec (the two-node CNI figure is a side-by-side
comparison that stays as ASCII). Delete it if it's still unused when you next tidy up.
**Source:** <https://github.com/kubernetes/community/tree/main/icons> (`icons/svg/resources/unlabeled`,
`icons/svg/infrastructure_components/unlabeled`)
**Licence:** Apache-2.0 **or** CC-BY-4.0, at the user's choice. We take **Apache-2.0**, which requires
retaining this notice but not per-page attribution.

> The Kubernetes Icons Set is licensed under a choice of either Apache-2.0 or CC-BY-4.0 (Creative
> Commons Attribution 4.0 International). Copyright The Kubernetes Authors.

Used on the Act V path diagrams (`src/lib/diagrams.ts`, specs `k8s-service-path` and
`k8s-ingress-path`), where the boxes are these named API objects and the official icon is therefore
the accurate label. Optimised with [svgo](https://github.com/svg/svgo) (`--multipass`), which stripped
Inkscape editor metadata and cut each file by roughly 60%; no paths or colours were altered. They keep
their Kubernetes blue (`#326ce5`) rather than being recoloured to the theme, because they are
identifying a real object rather than acting as interface furniture.

## Brand marks

**File:** `src/lib/brand-marks.ts` (path data inlined)
**Source:** <https://github.com/simple-icons/simple-icons> — `icons/{docker,kubernetes,linux}.svg`
**Licence:** CC0-1.0 (public domain dedication). No attribution required; this entry is provenance,
not obligation.

Vendored rather than added as a dependency: the npm package carries 3,000+ icons and this site needs
three. Regenerate by refetching those three files and extracting each single `<path d="…">`.

Used on the landing-page act cards for the three acts that are *about* a named technology — Act I
(the Linux kernel), Act IV (Docker), Act V (Kubernetes). Acts II and III keep a Lucide glyph, because
a protocol has no vendor.

### Trademark note

CC0 waives **copyright** in the drawing. It does not license the **trademark**. The Docker whale, the
Kubernetes helm and Tux are marks belonging to Docker Inc., the Linux Foundation and Linus Torvalds
respectively.

Their use here is nominative — identifying the technology each act teaches, on a card that links to
lessons about it. They are rendered as monochrome silhouettes tinted with the page's own accent, the
form simple-icons publishes them in for exactly this purpose, and they are not used as a logo for
this project, in its favicon, or in any way that implies those projects endorse or are affiliated with
this course. If that ever changes, re-read each project's brand guidelines first.

## Already-existing dependencies (for completeness)

| Asset | Licence | Where |
| --- | --- | --- |
| [Lucide](https://lucide.dev/) icons | ISC | `lucide-astro`, landing-page cards |
| [Aspekta](https://github.com/thomasjockin/aspekta) typeface | SIL OFL 1.1 | `src/styles/fonts/` |
| [Flexoki](https://stephango.com/flexoki) palette | MIT (via `starlight-theme-flexoki`) | the whole theme |
| [Mermaid](https://mermaid.js.org/) | MIT | `astro-mermaid`, 17 lesson diagrams |

## Drawn here, not sourced

**Files:** `src/components/Motif.astro` (eight 48×20 section motifs), `src/components/JourneyStrip.astro`
(the landing page's `write()` → ten acts → `read()` strip), `src/components/Diagram.astro`.
**Licence:** none needed — original work in this repo.

Path data written by hand, no icon set involved, because the point of each one is a claim about its act:
Act I's route never leaves its box, Act IV's is three routes merging into one, Act V's is one fanning
out to three. No stock glyph knows that. They are also the reason there is no illustration budget to
spend: the motifs, the strip and the built diagrams together carry the visual load.

## What is deliberately *not* here

No stock photography or generic vector illustration. The course's own pitch is "experiments you run
yourself, not diagrams you're asked to believe," and decorative imagery of server rooms or vector
people asserts expertise where the lessons demonstrate it. The animated diagrams
(`src/components/Diagram.astro`) are built from the lessons' own content for the same reason: an
explanatory animation has to know what it is drawing.
