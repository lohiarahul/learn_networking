# The lab

**Before you start, get Docker running.** Everything below is one container, and Docker Desktop must
be installed and running first:

```bash
brew install --cask docker          # or download Docker Desktop from docker.com/products/docker-desktop
open -a Docker                      # launch it; wait for the whale icon in the menu bar to settle
docker info >/dev/null 2>&1 && echo "Docker is up and running" || echo "Docker is NOT running — open the Docker app and wait"
```

The first container you run downloads the `nicolaka/netshoot` image (~600 MB); every run after that
is instant. Pre-pull it now if you'd rather not wait once you're mid-lesson:

```bash
docker pull nicolaka/netshoot
```

With that done, start the lab. Everything in this course runs in one container. Start it now, and keep it open in a couple of terminal tabs as you read — the experiments are written to be run, not admired.

```
docker run --rm -it --privileged nicolaka/netshoot
```

`nicolaka/netshoot` is a container image whose entire purpose is to contain networking tools. A normal application container is deliberately empty — no `dig`, no `tcpdump`, no `ss` — because every extra binary is extra attack surface and extra megabytes. That emptiness is a virtue in production and a misery when you are trying to find out why a connection is failing.

Netshoot is the opposite by design: `ip`, `ss`, `tcpdump`, `tshark`, `dig`, `curl`, `nc`, `socat`, `nmap`, `iperf3`, `conntrack`, `nsenter`, and a few dozen more, all in one image you can drop next to anything. It is the standard "I need to see what is happening on this network" container, and the same image Kubernetes operators attach to a running Pod with `kubectl debug`.

Read the flags one at a time, because each one removes a wall that would otherwise hide the things this course is about.

`--rm` deletes the container when you exit. Nothing you do here survives, which is exactly what you want for a lab: every session starts clean, and you cannot accumulate damage. Run a command that wrecks the routing table, type `exit`, run the `docker run` line again, and you are back to a pristine machine.

`-it` is two flags. `-i` keeps standard input open so the container reads what you type, and `-t` allocates a pseudo-terminal so you get a real interactive shell with a prompt, line editing, and color — rather than a dead pipe. Together they mean "give me a shell I can actually use." That pseudo-terminal, incidentally, is a file: it shows up in `/proc/self/fd` as descriptors 0, 1, and 2, which is the first thing you will look at in Act I.

`--privileged` is the big one. By default a container is a heavily de-clawed process: the kernel strips away dozens of capabilities so the container cannot reconfigure the network, load kernel modules, read most of `/proc` and `/sys`, or run a packet sniffer. That is correct for running an application and fatal for learning how the network works, because nearly every experiment here needs to either *change* the network stack (add a namespace, create a veth pair, write an iptables rule) or *watch* it at a level the kernel normally forbids (capture raw packets with `tcpdump`, read the connection-tracking table). `--privileged` hands the container the full set of capabilities, so it can do all of that. You would never run a production workload this way — a privileged container that gets compromised is, effectively, root on the host — and that danger is itself a lesson this course returns to. Here, in a throwaway lab, it is the price of being able to see.

You'll notice one flag is *missing* from that command: **`--network host`**. Add it and the container stops having its own interfaces, routes, and `/proc/net/tcp`, and starts seeing the host's instead. Sit with how odd that is for a moment — what *is* the thing a container normally has one of, that this flag makes it borrow? Hold that question; Act IV takes the mechanism apart and gives it a name. Meanwhile the flag is useful, and from **Act II onward you'll add it** to look at the machine's actual network:

```
docker run --rm -it --privileged --network host nicolaka/netshoot
```

But Act I is "one machine talking to itself," where the container's *own* network is exactly the point. And on **Docker Desktop (macOS/Windows), `--network host` is degraded** — a server you start inside becomes unreachable over loopback (`curl localhost` just fails). So for the orientation and Act I, leave it off; we bring it in deliberately, in Act II, when there's a real reason to.

So the bargain for now: `--rm` makes the lab disposable, `-it` makes it a usable shell, and `--privileged` lets you change and observe the kernel's network stack — a complete laboratory in one line.

From Act I you'll also compile and run small C programs — a tiny HTTP server you carry through the whole course. Plain `nicolaka/netshoot` has the tools but no compiler, so you'll switch to the **`netlab`** image (netshoot **plus** a C compiler, with the programs baked in). Build it once; the full run guide is in [the lab code guide](../code/README.md):

```
docker build -t netlab networking-fundamentals/code
```

That path is the folder holding the `Dockerfile`, so it depends on where the four source files are sitting. If you're following on the web and [made your own folder](../code/minihttp.c) instead of cloning, you're already inside it — so the path is just `.`:

```
docker build -t netlab .
```

Either way you end up with an image called `netlab` containing the sources at `/code`. **After this one command, the folder stops mattering.** Every other command in Acts I–IV runs *inside* the container and refers to `/code`, never to a path on your Mac — so you can build the image from anywhere and forget where you put it.

**A note on `eza`.** Throughout the course, every `ls` command is followed by an **eza twin** — `eza` is a modern rewrite of `ls` with colour, column headers, trees, and icons, and seeing the two side by side is a quick way to learn it. The `netlab` image already has `eza` baked in. In plain `nicolaka/netshoot` (which the orientation and the first two Act I lessons use), add it once at the start of your session:

```
apk add eza
```

The twins are always optional — the plain `ls` command above each one is the canonical, verified version. Run the twin when you want the prettier view.

Now read in order:

- **01 · [What is a process?](01-what-is-a-process.md)** — what a process actually is: a directory in `/proc`, file descriptors as integers, and why the `ls` that lists your open files opens one itself.
- **02 · [How processes communicate](02-how-processes-communicate.md)** — how processes use those descriptors to reach other processes and, eventually, other machines. The socket entry that the whole course is about.

Then open **[Act I — One machine talking to itself](../act-1-one-machine/README.md)** and begin.
