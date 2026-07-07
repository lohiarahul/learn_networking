/**
 * One-shot: convert the Aspekta TTFs in src/styles/fonts/ to WOFF2 beside them.
 *
 * Not part of the build. The fonts change roughly never, so the converted files are committed and this
 * script is kept only so the next person can see exactly how they were produced. Run it with
 * `node scripts/ttf2woff2.mjs` after dropping in a new weight.
 *
 * No subsetting, deliberately. WOFF2's Brotli compression is where nearly all of the saving is, and
 * subsetting a course that renders box-drawing characters, arrows and ✓/⚑ in prose is a good way to
 * discover a missing glyph six months later on one page nobody checks. The full face at WOFF2 is
 * already most of the win at none of the risk.
 *
 * Requires `wawoff2` (the Google woff2 encoder compiled to wasm — no native toolchain):
 *   npm install --no-save wawoff2
 */
import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { compress } from 'wawoff2';

const DIR = path.join(import.meta.dirname, '..', 'src', 'styles', 'fonts');

const files = (await readdir(DIR)).filter((f) => f.endsWith('.ttf')).sort();
if (files.length === 0) throw new Error(`no .ttf files in ${DIR}`);

let before = 0;
let after = 0;

for (const file of files) {
  const ttf = await readFile(path.join(DIR, file));
  const woff2 = Buffer.from(await compress(ttf));
  const out = file.replace(/\.ttf$/, '.woff2');
  await writeFile(path.join(DIR, out), woff2);
  before += ttf.length;
  after += woff2.length;
  console.log(
    `  ${file} → ${out}   ${(ttf.length / 1024).toFixed(1)} KB → ${(woff2.length / 1024).toFixed(1)} KB`,
  );
}

console.log(
  `\ntotal ${(before / 1024).toFixed(1)} KB → ${(after / 1024).toFixed(1)} KB ` +
    `(${(100 - (after / before) * 100).toFixed(0)}% smaller)`,
);
