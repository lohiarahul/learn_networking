# `docker`

The developer-facing view, and `docker network inspect` — Act IV's bridge and veth pairs, printed as JSON

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · obj-verb |
| **Mode** | mutate · live |
| **Taught in** | [the fd table](../../../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `docker --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-f` | (`inspect`) a Go template. `-f '{{.State.Pid}}'` is the pid, which is the handle every `nsenter` command needs |
| `--network` | which network mode. `host` means no namespace of its own, so the container's ports *are* the host's |
| `--privileged` | drop the capability and seccomp restrictions. Half the commands in this course need it, and it is worth knowing that is why they work |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### The developer-facing view of Act IV's mechanisms

| Command | What it gives you |
|---|---|
| `docker network inspect bridge` | the bridge, subnet and every attached container, as JSON |
| `docker inspect -f '{{.State.Pid}}' <c>` | the PID — the handle for nsenter |
| `docker run --rm -it --privileged --network host <img>` | no namespace of its own: the container is in the host's |
| `docker exec -it <c> sh` | nsenter with a friendlier face |
| `docker events` | stream container lifecycle events |

## As the course runs it

*11 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `docker build -t netlab networking-fundamentals/code` | `build` = build an image; `-t netlab` = tag (name) it; trailing path = the **build context**, the directory holding the `Dockerfile`. From your own folder of the four files that path is `.` — the only command in the course naming a path on your Mac | Starting the lab |
| `docker run --rm -it --privileged --name lab netlab` | `--rm` = delete the container on exit; `-it` = interactive + TTY; `--privileged` = full kernel access, which is what lets you edit routes and namespaces; `--name lab` = a name to `exec` into later. **Acts I only** | Starting the lab |
| `docker run --rm -it --privileged --network host --name lab nicolaka/netshoot` | `--network host` = **no network namespace of its own** — the container is *in the host's*. Acts II–IV need this, and it is why their drills change the host's real networking. `netshoot` carries the tools; `netlab` adds a C compiler | Starting the lab |
| `docker exec -it lab zsh` | `exec` = run a command in an *already running* container; `zsh` = the shell to start | Starting the lab |
| `docker run --rm -it --privileged -p 8080:8080 --name lab netlab` | `-p 8080:8080` = publish container port to host port. The DNAT rule this writes is opened up in Act IV | Lesson 5 — Ports and /proc/net/tcp |
| `docker diff <container>` | (run on your Mac) the writable layer's changes versus the image: `A` added, `C` changed/copied-up, `D` deleted (a whiteout). Reads `upperdir` for you | Lesson 6b — The container's filesystem (optional) |
| `docker volume create <name>` | a persistent volume — a separate filesystem, not part of any overlay | Lesson 6b — The container's filesystem (optional) |
| `docker run -v <vol>:/data …` | mount it at `/data`; writes there bypass the overlay and survive the container | Lesson 6b — The container's filesystem (optional) |
| `docker run --rm nicolaka/netshoot cat /sys/fs/cgroup/memory.max` | `max` unlimited by default | Lesson 1b — cgroups |
| `docker run --rm --memory 64m --memory-swap 64m nicolaka/netshoot cat /sys/fs/cgroup/memory.max` | `--memory` sets the limit; `--memory-swap` equal to it disables swap, so the limit is real. The file now reads `67108864` | Lesson 1b — cgroups |
| `docker run -d -p 8080:80 --name pub nginx` | `-d` detached; `-p 8080:80` publishes host 8080 to container 80 — and *writes the DNAT rule you are about to read* | Lesson 3 — iptables and NAT |
| `docker inspect -f '{{.HostConfig.NetworkMode}}' <c>` | which of the four network shapes this container actually got — `host`, `bridge`, `none`, or a custom network's name | Lesson 2b — Docker networks |
| `docker network inspect bridge --format '{{json .Containers}}'` | every container actually plugged into `docker0`, right now — the ground truth `brif/` also shows, in JSON | Lesson 2b — Docker networks |
| `docker network inspect <name> --format '{{.Id}}'` | a custom network's full ID — its first 12 hex characters, prefixed `br-`, are that network's real kernel bridge name | Lesson 2b — Docker networks |
