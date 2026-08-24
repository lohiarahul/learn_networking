/**
 * Which part of the course a page belongs to, and the motif that stands for it.
 *
 * Keyed on the first path segment, which the sync script derives from the source directory name —
 * so `networking-fundamentals/act-3-the-internet/05-tls.md` becomes `/act-3/05-tls/` and lands here
 * as `act-3`. Pages outside the course proper (`/course/`, `/progress/`, the landing page)
 * match nothing and get no header, which is the point: the marks should feel like chapter ornaments,
 * not site furniture.
 *
 * Labels deliberately echo the sidebar group names rather than inventing a second set of titles for
 * the same thing.
 */
export type MotifName =
  | 'orientation'
  | 'act-1'
  | 'act-2'
  | 'act-3'
  | 'act-4'
  | 'act-5'
  | 'act-6'
  | 'act-7'
  | 'act-8'
  | 'act-9'
  | 'act-10'
  | 'capstone'
  | 'reference'
  | 'exam-prep';

export interface Section {
  /** Shown as an eyebrow above the page title. */
  label: string;
  motif: MotifName;
  /**
   * The section's overview page, where it has one. The eyebrow links to it, which is what carries
   * the "up" navigation the lesson sources used to put in a footer line — `sync-content.mjs` drops
   * that block for exactly the sections listed here. Capstone and Reference have no overview page,
   * so their eyebrow is plain text and their footer nav survives.
   */
  href?: string;
}

const SECTIONS: Record<MotifName, Section> = {
  orientation: { label: 'Orientation · before the wire', motif: 'orientation', href: '/orientation/' },
  'act-1': { label: 'Act I · One machine', motif: 'act-1', href: '/act-1/' },
  'act-2': { label: 'Act II · Two machines', motif: 'act-2', href: '/act-2/' },
  'act-3': { label: 'Act III · The internet', motif: 'act-3', href: '/act-3/' },
  'act-4': { label: 'Act IV · One pretends to be many', motif: 'act-4', href: '/act-4/' },
  'act-5': { label: 'Act V · Kubernetes', motif: 'act-5', href: '/act-5/' },
  'act-6': { label: 'Act VI · The cluster that runs itself', motif: 'act-6', href: '/act-6/' },
  'act-7': { label: 'Act VII · Describing the work', motif: 'act-7', href: '/act-7/' },
  'act-8': { label: 'Act VIII · Trust on an untrusted wire', motif: 'act-8', href: '/act-8/' },
  'act-9': { label: 'Act IX · Identity and access', motif: 'act-9', href: '/act-9/' },
  'act-10': { label: 'Act X · Securing the cluster', motif: 'act-10', href: '/act-10/' },
  capstone: { label: 'Capstone', motif: 'capstone' },
  // Reference gained an overview page with the instrument-panel wing, so its eyebrow links up like an
  // act's rather than sitting as plain text. That also hands `tagLessonNav` the section, which is what
  // makes it drop each source's footer nav line in favour of Starlight's own pagination.
  reference: { label: 'Reference · the instrument panel', motif: 'reference', href: '/reference/' },
  // Not an act, and the label says so. exam-prep is rehearsal for a timed exam, which is the one
  // thing the course refuses to do inside a lesson — so it gets an eyebrow that never reads as
  // "Act XI".
  'exam-prep': { label: 'Exam prep · CKA and CKS', motif: 'exam-prep', href: '/exam-prep/' },
};

/**
 * `/learn/act-3/05-tls/` -> the Act III section. Returns null for anything not in a course section.
 *
 * Takes the pathname rather than a Starlight route object on purpose: the base path is the only
 * variable, and a URL is stable across Starlight versions in a way `entry.id` has not been.
 */
export function sectionForPath(pathname: string): Section | null {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const rest = base && pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
  const segments = rest.replace(/^\/+/, '').split('/').filter(Boolean);
  const section = segments[0] ? SECTIONS[segments[0] as MotifName] : undefined;
  if (!section) return null;

  // On the overview page itself the eyebrow would link to where you already are, so it goes plain.
  const onOverview = segments.length === 1;
  return {
    ...section,
    href: section.href && !onOverview ? `${base}${section.href}` : undefined,
  };
}
