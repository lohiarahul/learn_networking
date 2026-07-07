/**
 * review.ts — the self-graded checkpoints, and which of them are due again.
 *
 * A checkpoint is only worth interrupting a lesson for if the attempt goes somewhere. Grading your
 * own recall is the cheap part; the part that compounds is being shown the same question again after
 * enough time has passed to have half-forgotten it, which is what `due()` is for.
 *
 * The schedule is deliberately crude — three fixed intervals, no ease factors, no SM-2. A real
 * spaced-repetition algorithm earns its complexity over hundreds of cards reviewed daily; this is a
 * course with a few dozen checkpoints that a reader works through once and revisits occasionally, and
 * a schedule they can predict in their head ("missed ones come back tomorrow") is worth more here than
 * one that is theoretically optimal.
 */
const KEY = 'learn_networking:review:v1';

export type Grade = 'got' | 'notyet';

export interface ReviewEntry {
  /** Page the checkpoint lives on, e.g. `/act-3/tcp-states/`. */
  path: string;
  /** The question text, so the review list can show it without loading the page. */
  prompt: string;
  grade: Grade;
  /** When it was last graded, epoch ms. */
  at: number;
}

type Store = Record<string, ReviewEntry>;

const DAY = 86_400_000;

/**
 * How long until a checkpoint comes back, by the grade you last gave it.
 *
 * "Not yet" returns the next day rather than immediately: re-reading a thing you just failed is
 * re-reading, not retrieval, and the gap is what makes the second attempt worth anything.
 */
const INTERVAL: Record<Grade, number> = {
  notyet: 1 * DAY,
  got: 10 * DAY,
};

function read(): Store {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const out: Store = {};
    for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
      if (!v || typeof v !== 'object') continue;
      const e = v as Partial<ReviewEntry>;
      if (typeof e.path !== 'string' || typeof e.prompt !== 'string') continue;
      if (e.grade !== 'got' && e.grade !== 'notyet') continue;
      out[k] = { path: e.path, prompt: e.prompt, grade: e.grade, at: Number(e.at) || 0 };
    }
    return out;
  } catch {
    return {};
  }
}

function write(store: Store): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    /* storage unavailable — grading still works for this page view, it just won't persist */
  }
  document.dispatchEvent(new CustomEvent('ln:review'));
}

export function getGrade(key: string): ReviewEntry | null {
  return read()[key] ?? null;
}

export function setGrade(key: string, entry: Omit<ReviewEntry, 'at'>): void {
  const store = read();
  store[key] = { ...entry, at: Date.now() };
  write(store);
}

/** Everything graded, whether or not it is due. */
export function all(): Array<ReviewEntry & { key: string }> {
  return Object.entries(read()).map(([key, entry]) => ({ key, ...entry }));
}

/** Graded checkpoints whose interval has elapsed — hardest-first, so "not yet" leads the list. */
export function due(now = Date.now()): Array<ReviewEntry & { key: string }> {
  return all()
    .filter((e) => now - e.at >= INTERVAL[e.grade])
    .sort((a, b) => {
      if (a.grade !== b.grade) return a.grade === 'notyet' ? -1 : 1;
      return a.at - b.at;
    });
}
