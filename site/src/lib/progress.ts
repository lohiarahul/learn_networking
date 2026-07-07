/**
 * progress.ts — client-side lesson progress.
 *
 * Keyed on `location.pathname` rather than Starlight's internal entry ids: those ids are an
 * implementation detail of the content loader and have changed shape between Starlight versions,
 * whereas the URL scheme is ours (`/act-1/the-fd-table/`) and is exactly what sync-content.mjs
 * already guarantees. Counting per act is then a prefix match.
 *
 * Everything is local to the browser — no accounts, no network. Clearing site data resets it.
 */
const KEY = 'learn_networking:progress:v1';

/** Trailing slash always present, so `/act-1/x` and `/act-1/x/` can't both be stored. */
export function normalise(path: string): string {
  const p = path.split('?')[0]!.split('#')[0]!;
  return p.endsWith('/') ? p : `${p}/`;
}

export function read(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed)
      ? new Set(parsed.filter((v): v is string => typeof v === 'string'))
      : new Set();
  } catch {
    // Private-mode Safari and blocked-storage settings throw on access rather than returning null.
    return new Set();
  }
}

export function write(done: Set<string>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify([...done]));
  } catch {
    /* storage unavailable — the toggle still works for this page view, it just won't persist */
  }
  document.dispatchEvent(new CustomEvent('ln:progress', { detail: { size: done.size } }));
}

export function isDone(path: string): boolean {
  return read().has(normalise(path));
}

export function setDone(path: string, value: boolean): void {
  const done = read();
  const key = normalise(path);
  if (value) done.add(key);
  else done.delete(key);
  write(done);
}

/** How many stored paths sit under `/<prefix>/`, including the act's own index page. */
export function countUnder(prefix: string): number {
  const p = normalise(prefix);
  let n = 0;
  for (const path of read()) if (path.startsWith(p)) n++;
  return n;
}
