# learn_networking

A hands-on networking course — *how does `write()` on one machine become `read()` on another?* — published as an [Astro](https://astro.build) + [Starlight](https://starlight.astro.build) site out of `site/`, built from the plain Markdown in [`networking-fundamentals/`](networking-fundamentals/README.md).

This file only covers running that site. Everything about *doing* the course — the Docker lab, building the `netlab` image, Act V's Kubernetes cluster — lives in the course itself: start at [`networking-fundamentals/00-orientation/`](networking-fundamentals/00-orientation/README.md).

There are two published routes through the material. [`JOURNEY-MAP.md`](JOURNEY-MAP.md) is the course in narrative order — every idea earned before it is used. [`exam-prep/the-exam-path.md`](exam-prep/the-exam-path.md) is the same material in CKA/CKS order, with measured word counts per step and an explicit optional track. Pick one deliberately; they are for different goals.

## Running the site

```bash
git clone <this repository's URL>
cd learn_networking/site
npm install
npm run dev      # http://localhost:4321
npm run build    # static site into site/dist/
```

See [`site/README.md`](site/README.md) for how the build works — the Markdown-to-site sync, theming, and deploying the static output.
