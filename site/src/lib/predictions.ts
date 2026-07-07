/**
 * predictions.ts — what the reader committed to before running an experiment.
 *
 * Separate store from progress.ts on purpose: progress is one flag per page and is small enough to
 * keep as an array, whereas this is keyed text that grows with every prediction on every page.
 *
 * Why store it at all, rather than just revealing an answer: the value of a prediction is being able
 * to hold your own wrong answer next to the real one. A prompt you answer in your head and then read
 * past leaves nothing to compare, which is exactly how a reader talks themselves into "I knew that."
 * Persisting it means the chip is still sitting there, in your own words, while you read the result —
 * and still there tomorrow if you come back.
 *
 * Local to the browser, like progress: no accounts, no network.
 */
const KEY = 'learn_networking:predictions:v1';

type Store = Record<string, string>;

function read(): Store {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const out: Store = {};
    for (const [k, v] of Object.entries(parsed)) if (typeof v === 'string') out[k] = v;
    return out;
  } catch {
    // Private-mode Safari throws on access rather than returning null.
    return {};
  }
}

function write(store: Store): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    /* storage unavailable — the lock still works for this page view, it just won't persist */
  }
}

/**
 * A key that survives a lesson being edited.
 *
 * Ordinal within the page, not a hash of the prompt text: the prompts get reworded, and a reader who
 * comes back after an edit should still see the prediction they made against that experiment rather
 * than an empty box. Reordering the experiments in a lesson would mis-pair them, which is rare enough
 * to accept and harmless when it happens.
 */
function keyFor(path: string, index: number): string {
  const p = path.split('?')[0]!.split('#')[0]!;
  return `${p.endsWith('/') ? p : `${p}/`}#${index}`;
}

export function getPrediction(path: string, index: number): string | null {
  return read()[keyFor(path, index)] ?? null;
}

export function setPrediction(path: string, index: number, value: string): void {
  const store = read();
  store[keyFor(path, index)] = value;
  write(store);
}

export function clearPrediction(path: string, index: number): void {
  const store = read();
  delete store[keyFor(path, index)];
  write(store);
}

/** Every prediction the reader has committed to, newest-key-last. Used by the progress page. */
export function allPredictions(): Array<{ key: string; path: string; value: string }> {
  return Object.entries(read()).map(([key, value]) => ({
    key,
    path: key.split('#')[0]!,
    value,
  }));
}
