# The code, and running the lab on macOS

The small C programs the course carries through every act, plus the `netlab` image that builds and runs them. These are Linux programs — you never compile them on macOS directly. You build and run them *inside the container*, which works the same on Apple-Silicon or Intel Macs.

## What's here

```
code/
  minihttp.c    the spine: a ~40-line HTTP server you inspect, capture, and deploy across all five acts
  fd-demo.c     opens a file + a socket so you can watch the fd table grow
  Makefile      `make` builds both (run inside the container)
  Dockerfile    builds netlab = netshoot's tools + a C compiler
```

All four are printed in full, with their comments, at **[the code, in full](minihttp.c)** — read them there rather than taking the lessons' stripped excerpts on trust. The comments in `minihttp.c` are a third of what Act I teaches.

## One-time setup

With **Docker Desktop** running, build the image once:

```
docker build -t netlab networking-fundamentals/code
```

**No clone?** That command needs this directory as its build context, so it is the one step that assumes you have the repo. If you are working from the website, copy the four files off [the code page](minihttp.c) into an empty directory and run `docker build -t netlab .` there instead — the resulting image is identical, and every `docker run … netlab` in the course works against it.

`netlab` = everything in `nicolaka/netshoot` (`ss`, `tcpdump`, `dig`, `nc`, …) plus `cc`/`make`, with the sources baked in at `/code`.

## Running the lab

Acts I–IV run in one container. Name it so you can open more shells into it:

```
docker run --rm -it --privileged --name lab netlab
```

| Flag | Why |
|------|-----|
| `--rm` | disposable — `exit` wipes it clean |
| `-it` | interactive shell |
| `--privileged` | observe/change the kernel network stack (namespaces, tcpdump, iptables) |
| `--name lab` | so a second terminal can join it |

> **Act I omits `--network host` on purpose.** Act I is "one machine talking to itself," and on Docker Desktop `--network host` breaks loopback (`curl localhost` fails). **Act II adds it** when you want the host's real interfaces:
> ```
> docker run --rm -it --privileged --network host --name lab netlab
> ```

### A second shell into the same container

Many experiments want one shell running a server and another inspecting it. From a new macOS terminal:

```
docker exec -it lab zsh
```

### Build and run

Inside the container:

```
cc -o /tmp/fd-demo /code/fd-demo.c     # warm-up: opens a file + a socket, then waits
/tmp/fd-demo                            # inspect its fd table from a second shell

cc -o /tmp/minihttp /code/minihttp.c   # the spine
/tmp/minihttp 8080                      # run — prints its PID and listening fd
```

From a second shell into `lab`:

```
ls -la /proc/$(pgrep -n minihttp)/fd   # see its listening socket
curl localhost:8080                     # talk to it
```

### Editing the code and recompiling

This is the one command where the location of your files matters again — a mount has to name a real folder on your Mac. Mount whichever folder holds the `.c` files over `/code`:

```
# from a clone, at the repo root:
docker run --rm -it --privileged --name lab -v "$PWD/networking-fundamentals/code:/code" netlab

# from your own folder of the four files, standing in it:
docker run --rm -it --privileged --name lab -v "$PWD:/code" netlab
```

Edit `minihttp.c` in your Mac editor, then re-run `cc -o /tmp/minihttp /code/minihttp.c` inside the container to pick up changes.

This step is entirely optional — the sources are already baked into the image at `/code`, so every lesson works without it. You only want the mount if you intend to *change* the server and keep the changes.

## Gotchas on Docker Desktop (macOS)

- **`hostname` shows a random container id** — your containers run inside Docker Desktop's Linux VM.
- **`--network host` is degraded** here; it works fully only on native Linux. This course routes around it (see above).
- **`ulimit -n`** is large (often `1048576`); production containers are usually capped far lower.
- No Homebrew or compiler needed on the Mac — everything compiles inside the container.
