import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import mermaid from 'astro-mermaid';
import starlightThemeFlexoki from 'starlight-theme-flexoki';

// Deploying under a subpath (a GitHub Pages project site, say)? Set both of these and run the build;
// scripts/sync-content.mjs reads BASE_PATH too, so generated links pick up the same prefix.
const base = process.env.BASE_PATH || undefined;
const site = process.env.SITE_URL || 'https://learn-networking.pages.dev';

export default defineConfig({
  site,
  base,
  integrations: [
    // Must come before starlight: it needs first go at the Markdown pipeline.
    mermaid({
      // Colours are NOT set here — global.css restyles the rendered SVG instead, which keeps diagrams
      // theme-aware without duplicating a palette or forcing a re-render. This block is layout only.
      theme: 'base',
      autoTheme: false,
      enableLog: false,
      mermaidConfig: {
        // NOT 'inherit': Mermaid measures label text to size its nodes, and an unresolvable family
        // makes it mis-measure — which is what was clipping and overlapping labels.
        fontFamily: "'Aspekta', 'Inter', ui-sans-serif, system-ui, sans-serif",
        fontSize: 14,
        // nodeSpacing was 40, which left huge vertical gaps between the unconnected rows of a stacked
        // subgraph (the fd table) and made diagrams several screens tall.
        // `padding: 8` was too tight to fit a subgraph's own title: Mermaid lays the title on the
        // cluster's top edge and the first node inside then rode up over it, cutting the words in half
        // ("kernel — the real fd table" behind the `0 → terminal` box). `subGraphTitleMargin` is the
        // knob that reserves that space, so the diagrams stay compact without the collision.
        flowchart: {
          curve: 'basis',
          useMaxWidth: true,
          padding: 12,
          nodeSpacing: 12,
          rankSpacing: 44,
          subGraphTitleMargin: { top: 4, bottom: 10 },
        },
        sequence: { useMaxWidth: true, mirrorActors: false, wrap: true },
      },
    }),
    starlight({
      // Short, because it sits in the nav bar and is appended to every page title.
      title: 'learn_networking',
      description:
        'A hands-on networking course built around one question: how does write() on one machine '
        + 'become read() on another? Five acts, run in a throwaway Linux container and a real '
        + 'Kubernetes cluster — from the file-descriptor table to CNI.',
      // The design system is now a maintained, reading-optimised theme rather than a hand-rolled one.
      // Flexoki is Steph Ango's ink-on-paper palette, packaged by Starlight's own lead maintainer.
      // Swap the accent with: 'red' | 'orange' | 'yellow' | 'green' | 'cyan' | 'blue' | 'purple' | 'magenta'.
      plugins: [starlightThemeFlexoki({ accentColor: 'cyan' })],
      customCss: ['./src/styles/global.css'],
      // Expressive Code is left entirely to the theme, on purpose.
      //
      // Flexoki passes `themes: [light, dark]` with `codeBackground: ['#100f0f', '#fffcf0']` — it
      // deliberately *inverts* code blocks against the page: black code on paper in light mode, paper
      // code on black in dark mode. Either way there's real contrast.
      //
      // Forcing a single dark theme here (an earlier attempt at "make code blocks black") collapsed
      // that array to index 0, so `#100f0f` was used in both modes. In dark mode the page background is
      // also `#100f0f`, which made code blocks invisible — same colour as the page, delineated only by
      // a 3px border. Black code blocks are only possible on a light page; in dark mode they have to be
      // lighter than the background or they disappear. Don't re-add a `themes` override here.
      // On, but fed from frontmatter rather than from git: `sync-content.mjs` stamps each page with the
      // last commit date of its *source* file in networking-fundamentals/. Starlight's own git lookup
      // cannot work here, because the files it would inspect are generated and gitignored.
      //
      // The point is answering "is this still true?" — a fair first question of material this close to
      // kernel behaviour, and one nothing on the site used to answer.
      lastUpdated: true,
      pagination: true,
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      components: {
        // Adds the per-section og:image. Starlight declares a large-image Twitter card and ships no
        // image, so without this every share of the course previews as a bare text row.
        Head: './src/components/Head.astro',
        // Prepends the "mark as done" toggle, then defers to Starlight's own footer.
        Footer: './src/components/Footer.astro',
        // Adds a section eyebrow and motif above the <h1>. Restates Starlight's own h1 styles, which
        // stop shipping the moment the component is overridden.
        PageTitle: './src/components/PageTitle.astro',
      },
      sidebar: [
        {
          label: 'Start here',
          items: [
            { slug: 'course' },
            { slug: 'progress' },
          ],
        },
        {
          label: 'Orientation — before the wire',
          items: [{ autogenerate: { directory: 'orientation' } }],
        },
        {
          label: 'Act I — One machine',
          collapsed: true,
          items: [{ autogenerate: { directory: 'act-1' } }],
        },
        {
          label: 'Act II — Two machines',
          collapsed: true,
          items: [{ autogenerate: { directory: 'act-2' } }],
        },
        {
          label: 'Act III — The internet',
          collapsed: true,
          items: [{ autogenerate: { directory: 'act-3' } }],
        },
        {
          label: 'Act IV — One pretends to be many',
          collapsed: true,
          items: [{ autogenerate: { directory: 'act-4' } }],
        },
        {
          label: 'Act V — Kubernetes',
          collapsed: true,
          items: [{ autogenerate: { directory: 'act-5' } }],
        },
        {
          label: 'Capstone',
          items: [{ autogenerate: { directory: 'capstone' } }],
        },
        {
          label: 'Reference',
          collapsed: true,
          items: [{ autogenerate: { directory: 'reference' } }],
        },
      ],
    }),
  ],
});
