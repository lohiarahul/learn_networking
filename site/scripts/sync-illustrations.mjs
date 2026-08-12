#!/usr/bin/env node
/**
 * sync-illustrations.mjs — project the topic illustrations into the site's public assets.
 *
 * `illustrations/` at the repo root is the single source of truth: the SVGs there are build output of
 * the Python generator in `illustrations/_build/`, and they are the copy that renders on GitHub when a
 * lesson references one relatively (`../../illustrations/07-security/https.svg`).
 *
 * The site needs the same files under a URL, so this script copies them into `site/public/` — the same
 * one-way projection `sync-content.mjs` performs for the lesson Markdown, and for the same reason:
 * a hand-maintained second copy drifts. Everything this script writes is gitignored.
 *
 * It also generates the contact-sheet gallery at `/illustrations/`, so that page can never fall out of
 * step with the set it is showing.
 *
 * Run `npm run sync`; `npm run dev` and `npm run build` do it for you.
 */
import { readFile, writeFile, mkdir, readdir, copyFile, unlink, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../..');
const SRC = path.join(REPO, 'illustrations');
const OUT = path.resolve(HERE, '../public/illustrations');

/** Same knob as astro.config.mjs and sync-content.mjs, so gallery URLs survive a subpath deploy. */
const BASE = (process.env.BASE_PATH ?? '').replace(/\/+$/, '');

/** Category directories are numbered (`01-fundamentals`); `_build` and `_previews` are not, and are
 *  deliberately excluded — the generator and its PNG proof sheets are not site assets. */
const CATEGORY_RE = /^\d\d-[a-z0-9-]+$/;

/** Folder name -> the heading the gallery shows. Anything unlisted falls back to its slug. */
const TITLES = {
  '01-fundamentals': 'Fundamentals',
  '02-addressing': 'Addressing',
  '03-switching-layer2': 'Switching & Layer 2',
  '04-routing-layer3': 'Routing & Layer 3',
  '05-transport': 'Transport Layer',
  '06-core-services': 'Core Services',
  '07-security': 'Security',
  '08-wireless': 'Wireless',
  '09-cloud-modern': 'Cloud & Modern Networking',
  '10-containers-and-kubernetes': 'Containers & Kubernetes',
  '11-application-layer': 'Application Layer',
};

const esc = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/**
 * Every illustration carries its own one-line `aria-label`, written next to the drawing code. Reading
 * it back here means the gallery's captions and the alt text a lesson should use come from the file
 * itself rather than a list that has to be kept in step.
 */
function ariaLabel(svg, file) {
  const m = svg.match(/aria-label="([^"]*)"/);
  if (!m) throw new Error(`${file} has no aria-label — every illustration needs one for alt text`);
  return m[1];
}

async function categories() {
  if (!existsSync(SRC)) return [];
  const entries = await readdir(SRC, { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory() && CATEGORY_RE.test(e.name))
    .map((e) => e.name)
    .sort();
}

async function main() {
  const cats = await categories();
  if (!cats.length) {
    // Not fatal: someone may be building the site without the illustration set present.
    console.log('sync-illustrations: no illustrations/ categories found — skipping');
    return;
  }

  await mkdir(OUT, { recursive: true });

  const manifest = [];
  let copied = 0;

  for (const cat of cats) {
    const files = (await readdir(path.join(SRC, cat))).filter((f) => f.endsWith('.svg')).sort();
    await mkdir(path.join(OUT, cat), { recursive: true });

    const rows = [];
    for (const file of files) {
      const from = path.join(SRC, cat, file);
      const svg = await readFile(from, 'utf8');
      rows.push({ file, slug: file.replace(/\.svg$/, ''), label: ariaLabel(svg, `${cat}/${file}`) });
      await copyFile(from, path.join(OUT, cat, file));
      copied += 1;
    }

    // Prune anything left over from a renamed or deleted illustration, so the published set is
    // exactly what the source directory holds.
    const keep = new Set(files);
    for (const stale of await readdir(path.join(OUT, cat))) {
      if (!keep.has(stale)) await unlink(path.join(OUT, cat, stale));
    }

    manifest.push({ cat, title: TITLES[cat] ?? cat, rows });
  }

  // A category folder that disappears upstream should not linger here either.
  const wanted = new Set(cats);
  for (const entry of await readdir(OUT, { withFileTypes: true })) {
    if (entry.isDirectory() && !wanted.has(entry.name)) {
      await rm(path.join(OUT, entry.name), { recursive: true, force: true });
    }
  }

  await writeFile(path.join(OUT, 'index.html'), gallery(manifest, copied), 'utf8');

  const total = manifest.reduce((n, c) => n + c.rows.length, 0);
  console.log(
    `sync-illustrations: ${total} illustrations in ${cats.length} categories -> public/illustrations/`
  );
}

/**
 * The gallery is a plain static page rather than a Starlight route on purpose: it is a contributor
 * tool for spotting style drift across the whole set, not course content, and it must keep working
 * without the content pipeline. It is themed to match the site so the illustrations are judged
 * against the background they will actually sit on.
 */
function gallery(manifest, count) {
  const parts = [
    `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Illustration set — ${count} spot illustrations</title>
<style>
  :root { color-scheme: light dark; --bg:#fffcf0; --ink:#100f0f; --dim:#6f6e69; --line:#e6e4d9; --card:#fff; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#100f0f; --ink:#cecdc3; --dim:#878580; --line:#282726; --card:#1c1b1a; }
  }
  * { box-sizing:border-box; }
  body { margin:0; padding:32px clamp(16px,4vw,48px) 96px; background:var(--bg); color:var(--ink);
         font:16px/1.55 ui-sans-serif,system-ui,-apple-system,sans-serif; }
  header { max-width:70ch; }
  h1 { font-size:1.6rem; margin:0 0 8px; letter-spacing:-.01em; }
  p.lede { color:var(--dim); margin:0; }
  p.note { color:var(--dim); font-size:.85rem; margin:14px 0 0; padding:10px 14px;
           border-left:3px solid var(--line); }
  h2 { font-size:1.05rem; margin:56px 0 4px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  h2 span { color:var(--dim); font-weight:400; font-size:.85rem; margin-left:8px; }
  .grid { display:grid; gap:20px; margin-top:20px;
          grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); }
  figure { margin:0; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
  figure img { display:block; width:100%; height:auto; border-radius:6px; }
  figcaption { margin-top:10px; font-size:.72rem; color:var(--dim); }
  figcaption b { display:block; color:var(--ink); font-size:.8rem; margin-bottom:3px;
                 font-family:ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-all; }
</style></head><body>
<header>
  <h1>Illustration set</h1>
  <p class="lede">${count} flat-vector spot illustrations, one per topic. 320&times;240 SVG, no text in
  the artwork, all composed from one shared primitive library.</p>
  <p class="note">Generated by <code>scripts/sync-illustrations.mjs</code> from
  <code>illustrations/</code>. Edit the drawings there, not here &mdash; everything under
  <code>public/illustrations/</code> is overwritten on the next <code>npm run sync</code>.</p>
</header>`,
  ];

  for (const { cat, title, rows } of manifest) {
    parts.push(
      `<h2>${esc(title)}<span>${rows.length} files &middot; ${cat}/</span></h2>`,
      '<div class="grid">'
    );
    for (const { file, slug, label } of rows) {
      parts.push(
        `<figure><img src="${BASE}/illustrations/${cat}/${file}" alt="${esc(label)}"` +
          ` loading="lazy" width="320" height="240">` +
          `<figcaption><b>${slug}</b>${esc(label)}</figcaption></figure>`
      );
    }
    parts.push('</div>');
  }

  parts.push('</body></html>');
  return parts.join('\n');
}

await main();
