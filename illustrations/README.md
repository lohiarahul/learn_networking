# Networking spot illustrations

76 flat-vector spot illustrations, one per topic, generated as hand-written SVG. No
image-generation API was used and nothing is vendored from a third party — every
shape in here is drawn by the primitive library in `_build/prims.py`.

## The design system

These are **spot illustrations**, not diagrams. They sit beside Mermaid figures and
shell blocks and are meant to be glanced at, not studied — so they carry no text and
stay deliberately under-detailed.

| Property | Value |
| --- | --- |
| Canvas | `320 × 240`, rounded `#f1f5f9` plate (`rx=18`) |
| Palette | plate `#f1f5f9` · surfaces `#ffffff` · primary `#3b82f6` · dark `#1e293b` · mid `#94a3b8` |
| Derived colour | `#dbeafe` — the one addition, a soft wash of the primary, used for fills |
| Line weight | `2.2` for every outline; `1.4–1.8` for interior detail; heavier only for a deliberately emphasised path |
| Corners | round caps and joins throughout |
| Text | none — no letters, digits or glyphs anywhere in the artwork |
| People | none |

Two rules are worth stating because breaking them is what makes a set look
machine-assembled:

1. **Flat, with one exception.** Everything is flat 2D except the packet, which is
   always the same isometric cube. "A packet is a cube" holds across all 76 images.
2. **Pills live inside containers.** A pill (`pill()`) stands in for text. Floating one
   on the bare plate makes the image read as unloaded skeleton UI, so pills only ever
   appear inside a card, bar, chip or table. Use `chip()` to hang an address or name
   off a device.

Accessibility: each file carries a `role="img"` and an `aria-label` describing what is
depicted, so the SVG can be inlined without extra markup.

## Shape vocabulary

The primitives are shared across every image, which is what makes the set cohere:

- **Devices** — `router` (pill chassis + crossing arrows), `switch_dev` (rectangular
  chassis + port row), `hub`, `bridge`, `rack`, `laptop`, `phone`, `access_point`,
  `proxy_box`
- **Structures** — `cloud`, `globe`, `hexagon`, `brick_wall`, `dashed_boundary`
  (any zone, namespace, VLAN or VPC), `pipe`, `stack`
- **Data** — `packet` (the isometric cube), `frame` (flat, with header and trailer
  bands), `addr_bar`, `bit_ruler`, `table_card`, `card`, `chip`, `tag`, `pill`
- **Security** — `shield`, `padlock`, `key`, `magnifier`, `pin`
- **Flow** — `arrow`, `curve_arrow`, `cable`, `waves`, `lifeline`, `node`
- **Signals** — `sine`, `square_wave`, `sawtooth`
- **Verdicts** — `check_badge`, `x_badge`
- **Other** — `gear`, `clock`

`router` and `switch_dev` are deliberately different silhouettes (pill vs rectangle) so
they stay distinguishable at 200px. Two earlier attempts are recorded in the code as
comments: a four-way arrow cross on the router read as a *move cursor*, and a solid
dark band on the bridge read as a *capacitor symbol*.

## Layout

```
illustrations/
├── 01-fundamentals/          08 files
├── 02-addressing/            10
├── 03-switching-layer2/      08
├── 04-routing-layer3/        10
├── 05-transport/             06
├── 06-core-services/         08
├── 07-security/              12
├── 08-wireless/              06
├── 09-cloud-modern/          08
├── _previews/                contact-sheet PNGs (gitignored — regenerate with sheet.py)
├── _build/                   the generator (source of truth)
└── MANIFEST.md               topic → filename → category
```

## Regenerating

Each category is one script. Editing a composition means editing its function, not the
SVG — the SVGs are build output.

```sh
cd _build
python3 b1_fundamentals.py          # rewrites ../01-fundamentals/*.svg
python3 sheet.py ../01-fundamentals /tmp/b1.png 4   # contact sheet for eyeballing
```

`sheet.py` needs `rsvg-convert` (`brew install librsvg`); nothing else has dependencies.

Changing anything in `prims.py` affects every image, so rebuild all nine scripts and
re-check the contact sheets afterwards.

## Using these in the Astro site

The files are plain SVG with no external references, so any of these work:

- `cp -r 0*/ ../site/public/illustrations/` and reference `/illustrations/<cat>/<slug>.svg`
- import from `src/assets/` to get Astro's asset pipeline and hashing
- inline the file contents directly to allow CSS control over the shapes

**One caveat worth deciding on before you wire these in:** the site's theme is Flexoki
(warm paper, `#100f0f` ink) and this palette is cool blue/slate, as specified. On a
Flexoki page they will read as foreign objects. If you want them to belong, the fix is
a one-line change — remap the six constants at the top of `prims.py` to Flexoki
equivalents and rebuild all nine scripts.
