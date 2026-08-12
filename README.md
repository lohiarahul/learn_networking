# learn_networking — start here

A hands-on networking course built around one question: *how does `write()` on one machine become `read()` on another?* You answer it by running experiments, not by reading diagrams. Acts I–IV happen inside a single throwaway Linux container; Act V runs a real Kubernetes cluster on your laptop; and every act carries an `in-the-wild.md` companion that re-runs its ideas on your actual Mac.

This page is the doorway. Work through the setup below — it takes about ten minutes, most of it Docker downloading — then open [the reading path](networking-fundamentals/README.md).

## What you need, and when

| Part of the course | What it needs |
|---|---|
| Reading any lesson | nothing — it's all on the web |
| Acts I–IV experiments | Docker, plus the `netlab` image you build in step 3 |
| Act V (Kubernetes) | Docker, plus `kind` and `kubectl` |
| The `in-the-wild.md` companions | nothing — built-in macOS tools only |

The setup commands below are written for macOS. On Linux, skip Homebrew and install Docker, `kind` and `kubectl` from your distribution instead; everything after that is identical.

### 1. Get the course files

Acts I–IV compile two small C programs — a file-descriptor demo and a tiny HTTP server you carry through the whole course. There are two ways to get them, and **neither one is second-class**.

**Cloning:**

```bash
git clone <this repository's URL>    # e.g. git clone https://github.com/you/learn_networking.git
cd learn_networking
```

Where a command on this page names a path, it's relative to that repo root. `books/CSAPP_2016.pdf` in there is the textbook the course is anchored to (not tracked in git — see `.gitignore` — so grab your own copy if you cloned).

**Not cloning:** the four files are published in full — sources and comments — on [the code page](networking-fundamentals/code/minihttp.c). Copy them into an empty directory:

```bash
mkdir netlab && cd netlab
# save minihttp.c, fd-demo.c, Makefile and Dockerfile from that page here
```

That directory is all step 3 needs. Nothing else in the course reads from the repo — the lessons work against the *image* you are about to build, not against your filesystem — so if you are reading on the web, this is the whole of the difference.

### 2. Docker — required for every experiment

Acts I–IV happen inside one disposable Linux container, and Act V builds its Kubernetes cluster out of Docker containers too, so Docker must be installed **and running**.

```bash
brew install --cask docker          # or download Docker Desktop from docker.com/products/docker-desktop
open -a Docker                      # launch it; wait for the whale icon in the menu bar to settle
docker info >/dev/null 2>&1 && echo "Docker is up and running" || echo "Docker is NOT running — open the Docker app and wait"
```

The first run downloads the `nicolaka/netshoot` image (~600 MB); every run after that is instant. Pre-pull it now if you like:

```bash
docker pull nicolaka/netshoot
```

### 3. Build the `netlab` image — required from Act I, lesson 1

`nicolaka/netshoot` has the networking tools but no C compiler. `netlab` is netshoot plus a compiler, with the course's two programs already built inside it. Build it once — from the repo root if you cloned, or from the directory you made in step 1 if you didn't:

```bash
docker build -t netlab networking-fundamentals/code   # cloned
docker build -t netlab .                              # from your own directory
```

Either produces the same image, with the sources at `/code` inside it, which is where every lesson expects them. That's what Act I starts with (`docker run --rm -it --privileged --name lab netlab`). The full guide, including how to mount the source so you can edit and recompile, is in [`networking-fundamentals/code/README.md`](networking-fundamentals/code/README.md), and the four files themselves are on [the code page](networking-fundamentals/code/minihttp.c).

### 4. kind + kubectl — required for Act V only

`kind` ("Kubernetes IN Docker") builds a cluster out of Docker containers, so Docker must be running first. Homebrew is the easiest route on macOS — check with `brew --version`, and install it from [brew.sh](https://brew.sh) if you don't have it.

```bash
brew install kind kubectl
kind --version && kubectl version --client     # confirm both are installed
```

Act V's cluster setup — creating the two-node cluster, and the two ways to get a shell inside it — is in [the Act V lab guide](networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md). Give Docker Desktop at least 4 GB of memory before you start it.

### 5. Optional niceties

A few `in-the-wild.md` commands reach for tools that aren't built into macOS. Each has a built-in fallback, so these are entirely optional:

```bash
brew install mtr      # per-hop latency and loss
brew install ldns     # provides `drill`, a DNSSEC-friendly dig
brew install dog      # a colourful dig
```

Everything else those companions use — `lsof`, `dig`, `tcpdump`, `nettop`, `networkQuality`, `arp`, `ping`, `traceroute` — already ships with macOS.

## Start here

With Docker running, open the course's own front page — it lists the five acts in order and what each one teaches:

**→ [`networking-fundamentals/README.md`](networking-fundamentals/README.md)**

Read [the orientation](networking-fundamentals/00-orientation/README.md) first: the lab setup, plus two short pages on what a process is and how two of them could ever talk. Then follow the acts in order.

Your very first lab command — which works from any directory once Docker is running — is the one the orientation explains flag by flag:

```bash
docker run --rm -it --privileged nicolaka/netshoot
```

## How far the road goes

The **built** course runs from the orientation through Act V: `write()` → sockets → two machines → the internet → containers → Kubernetes networking. Cryptography and identity (Stages 4–5) and AWS networking and security (Stages 8–9) are mapped but **not yet written** — see the roadmap banner in [`JOURNEY-MAP.md`](JOURNEY-MAP.md) for exactly where the built road ends.
