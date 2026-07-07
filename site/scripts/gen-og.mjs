/**
 * gen-og.mjs — build the social cards, one per section, into `public/og/`.
 *
 * Why this exists: every page declared `twitter:card = summary_large_image` and shipped no image, so
 * every Slack paste and every link preview of 127,000 words rendered as a bare text row. A course that
 * spreads by being shared needs the share to look like something.
 *
 * Why nine images and not seventy: an OG card is read at thumbnail size in a chat client, where a
 * lesson title is unreadable and the *act* is the useful unit — "Act III · The internet" tells someone
 * what they are being sent. Per-page cards would also mean 70 PNGs regenerated on every content edit
 * for no gain in what the reader learns from the preview.
 *
 * Why sharp and not a rendering library: sharp is already a dependency (Astro pulls it for image
 * optimisation), and librsvg — which is what sharp rasterises SVG with — handles this card fine. The
 * alternative (`astro-og-canvas`, satori + resvg) means a new dependency and a wasm payload to draw
 * nine static images that change about twice a year.
 *
 * The one real constraint: librsvg resolves `font-family` against *system* fonts and will not load
 * Aspekta from `src/styles/fonts/`. So the card is set in a system stack rather than the site's own
 * face — see FONT below. That is a deliberate trade, not an oversight: the alternative is embedding a
 * font rasteriser to make nine images match a typeface nobody is comparing them against side by side.
 *
 * Run automatically by `npm run build` (before astro build, so the PNGs exist for the copy into dist).
 * Re-run by hand with `node scripts/gen-og.mjs`.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const OUT = path.join(import.meta.dirname, '..', 'public', 'og');

/* Flexoki, the same values the site's theme resolves to. Kept literal because this file produces a
   raster: there is no cascade to inherit from, and a PNG cannot be theme-aware. The card commits to
   the dark ground for the same reason `.kz-terminal` does — it is the course's own material, and it
   holds up in both a light and a dark chat client. */
const INK = '#100f0f';
const BASE_200 = '#cecdc3';
const BASE_500 = '#878580';
const BASE_700 = '#575653';
const BASE_850 = '#343331';
const CYAN = '#3aa99f';

/* Ends in `sans-serif` so librsvg always resolves *something*; the named faces are the ones likely to
   be present on a build machine, in descending order of resemblance to Aspekta's low-contrast
   grotesque. */
const FONT = "'Helvetica Neue', Helvetica, Arial, 'DejaVu Sans', sans-serif";
const MONO = "'SF Mono', Menlo, 'DejaVu Sans Mono', 'Courier New', monospace";

const W = 1200;
const H = 630;

/**
 * The nine cards. `eyebrow`/`title` echo `src/lib/sections.ts` and the sidebar rather than inventing a
 * second set of names for the same things; `act` lights that stop on the journey strip.
 */
const CARDS = [
  {
    id: 'default',
    eyebrow: 'A hands-on networking course',
    title: 'Understand the network your code runs on',
    blurb: 'How does write() on one machine become read() on another?',
    act: 0,
  },
  {
    id: 'orientation',
    eyebrow: 'Orientation · before the wire',
    title: 'What a process is, and how two could ever talk',
    blurb: 'Set up the one-line lab, then start from the beginning.',
    act: 0,
  },
  {
    id: 'act-1',
    eyebrow: 'Act I · One machine',
    title: 'One machine talking to itself',
    blurb: 'The fd table, the socket object, and /proc/net/tcp read by hand.',
    act: 1,
  },
  {
    id: 'act-2',
    eyebrow: 'Act II · Two machines',
    title: 'Two machines on one wire',
    blurb: 'Trace a name to an IP to a route to a MAC — then subnet it on paper.',
    act: 2,
  },
  {
    id: 'act-3',
    eyebrow: 'Act III · The internet',
    title: 'The internet',
    blurb: 'Watch TCP build a reliable stream on top of a network that drops packets.',
    act: 3,
  },
  {
    id: 'act-4',
    eyebrow: 'Act IV · One pretends to be many',
    title: 'One pretends to be many',
    blurb: 'Build container networking from the kernel primitives underneath it.',
    act: 4,
  },
  {
    id: 'act-5',
    eyebrow: 'Act V · Kubernetes',
    title: 'Kubernetes networking',
    blurb: 'Who wires up a fleet, declaratively — and how do you debug it?',
    act: 5,
  },
  {
    id: 'capstone',
    eyebrow: 'Capstone',
    title: 'One packet, five acts',
    blurb: 'Follow a single packet from write() to read(), with the file that proves each layer.',
    act: 5,
  },
  {
    id: 'reference',
    eyebrow: 'Reference',
    title: 'The journey map',
    blurb: 'What is built, what is planned, and where the road ends for now.',
    act: 0,
  },
];

/** `&` in a title would otherwise end the SVG document. */
const esc = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/**
 * Wrap by measured-ish width. librsvg has no text layout, so a long title has to be broken into
 * explicit lines here — there is no `text-wrap` to lean on. 0.52em per character is the average
 * advance for a grotesque at this weight, which is close enough for a two-line headline.
 */
function wrap(text, size, maxWidth) {
  const perChar = size * 0.52;
  const limit = Math.floor(maxWidth / perChar);
  const lines = [];
  let line = '';
  for (const word of text.split(' ')) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > limit && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** The landing page's journey strip, at card scale, with `act` lit. `act: 0` lights nothing. */
function strip(act) {
  /* x0 leaves room for the right-anchored `write()` label to sit inside the 72px margin rather than
     running off the left edge of the canvas — there is no overflow to catch it here. */
  const x0 = 168;
  const x1 = 568;
  const y = 540;
  const stops = [1, 2, 3, 4, 5].map((n) => ({
    n,
    x: x0 + ((x1 - x0) / 4) * (n - 1),
  }));

  const numerals = { 1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V' };

  return `
    <text x="${x0 - 12}" y="${y + 5}" text-anchor="end" font-family="${MONO}" font-size="17" fill="${BASE_500}">write()</text>
    <path d="M${x0} ${y}H${x1}" stroke="${BASE_700}" stroke-width="2" fill="none"/>
    <text x="${x1 + 14}" y="${y + 5}" font-family="${MONO}" font-size="17" fill="${BASE_500}">read()</text>
    ${stops
      .map((s) => {
        const on = s.n === act;
        return `<circle cx="${s.x}" cy="${y}" r="${on ? 9 : 6}" fill="${on ? CYAN : INK}" stroke="${on ? CYAN : BASE_700}" stroke-width="2"/>
        <text x="${s.x}" y="${y + 34}" text-anchor="middle" font-family="${FONT}" font-size="15" font-weight="600" letter-spacing="1.2" fill="${on ? CYAN : BASE_700}">${numerals[s.n]}</text>`;
      })
      .join('\n    ')}`;
}

function card({ eyebrow, title, blurb, act }) {
  const titleSize = title.length > 34 ? 62 : 74;
  const titleLines = wrap(title, titleSize, W - 144);
  const titleTop = 232;
  const lineHeight = Math.round(titleSize * 1.14);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${INK}"/>

  <!-- The accent edge: the one piece of colour, and it reads even as a 200px-wide thumbnail. -->
  <rect x="0" y="0" width="7" height="${H}" fill="${CYAN}"/>

  <text x="72" y="103" font-family="${MONO}" font-size="22" letter-spacing="2.6" fill="${BASE_500}">${esc(
    eyebrow.toUpperCase(),
  )}</text>

  <path d="M72 137H${W - 72}" stroke="${BASE_850}" stroke-width="1.5" fill="none"/>

  ${titleLines
    .map(
      (l, i) =>
        `<text x="72" y="${titleTop + i * lineHeight}" font-family="${FONT}" font-size="${titleSize}" font-weight="600" fill="${BASE_200}">${esc(
          l,
        )}</text>`,
    )
    .join('\n  ')}

  ${wrap(blurb, 30, W - 320)
    .map(
      (l, i) =>
        `<text x="72" y="${titleTop + titleLines.length * lineHeight + 34 + i * 42}" font-family="${FONT}" font-size="30" fill="${BASE_500}">${esc(
          l,
        )}</text>`,
    )
    .join('\n  ')}

  ${strip(act)}

  <text x="${W - 72}" y="${H - 56}" text-anchor="end" font-family="${MONO}" font-size="21" fill="${BASE_700}">learn_networking</text>
</svg>`;
}

await mkdir(OUT, { recursive: true });

for (const c of CARDS) {
  const svg = card(c);
  const png = await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toBuffer();
  await writeFile(path.join(OUT, `${c.id}.png`), png);
}

console.log(`og: wrote ${CARDS.length} cards to public/og/`);
