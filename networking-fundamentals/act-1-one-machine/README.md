# Act I — One machine talking to itself

In 1971, Dennis Ritchie and Ken Thompson had a machine that could run several programs at once and a problem with no obvious solution: those programs needed to cooperate. A compiler had to hand its output to an assembler. A shell had to feed one command's output into the next. But the moment you let one program reach into another program's memory to drop off data, you have built a machine where any program can corrupt any other, and the whole edifice falls over the first time someone makes a mistake — which, on a shared university computer, is roughly every four minutes.

So the safe answer was strict isolation: give each process a private address space it cannot escape. And that answer creates the dilemma this entire act lives inside: **a process sealed off well enough to be safe cannot, by definition, reach anything outside itself — so how can two of them cooperate at all?**

Sit in that contradiction for a moment, because it is genuinely hard. Ritchie's way out sounds, the first time you hear it, almost too simple to be real — so we are not going to hand it to you here and ask you to nod along. You are going to walk into the dilemma yourself, try the obvious escapes, watch them come up short, and arrive at his answer the way he must have. When you do, a sentence you may have heard a hundred times without ever *feeling* will finally have weight behind it. Hold the question; the act is the answer.

This act stays on one machine and watches it talk to itself, because every confusing thing about networking is already present here, in miniature, with the wire removed.

You will start with the file-descriptor table — the private integer table that is a program's entire relationship with the outside world — and a tiny C program that makes a file and a socket appear in it side by side. Then the socket itself: not a thing your program holds, but a handle to a rich object the kernel keeps, with an identity, two buffers, and a state.

Then you build that idea into minihttp — a real listening server — by watching the kernel run the `socket`/`bind`/`listen`/`accept` ritual one call at a time, and you meet the limit that runs out when a busy server stops being able to accept connections. Then the loopback interface, `127.0.0.1`, the software-only device that carries `curl localhost` to your server with no hardware in the way, letting you measure the irreducible cost of the kernel's network stack.

Then ports and `/proc/net/tcp`, the kernel's own ledger of every socket on the machine, written in little-endian hex, which you learn to read by hand so that every tool that claims to show you connections becomes just a program that reads this one file and tidies the output. Then the **state** every socket carries — the precise sequence TCP walks from handshake to teardown — which, once you can read it, explains how a port scanner maps your machine while your application never notices, and why detecting that belongs in the kernel.

And finally a step back to ask what all those `/proc` files you trusted actually *are* — inodes, `mount`, and the virtual filesystem — until the sentence the act has been circling, **everything is a file**, stops being a slogan and becomes something you can defend down to the function pointer.

After this act you will be able to look at any process and enumerate exactly what it can touch, explain why `socket()` returns an integer and what that integer indexes, decode a raw row of `/proc/net/tcp` without a tool, and trace a local connection from the first system call to the last. You will own the vocabulary the rest of the course assumes — and you will be ready to say, and actually believe, the one sentence everything later is built on.

## The lessons — read in this order

Work through these in order. Each one runs experiments in the lab container and ends with a link to the next, so you never have to guess where to go. **One image switch:** you begin in plain `nicolaka/netshoot`, but partway through lesson 1 you compile a small C program and switch to the **`netlab`** image (netshoot + a compiler, with the course's C baked in) — lesson 1 tells you exactly when and how, and you stay in `netlab` for the rest of Act I.

1. **[The file-descriptor table](01-the-fd-table.md)** — the private integer table that is a program's entire link to the outside world, and a tiny C program (`fd-demo`) that puts a file and a socket in it side by side.
2. **[What a socket really is](02-the-socket-object.md)** — why the socket is just an integer in your process, but a handle to a kernel object with an identity, two buffers, and a state.
3. **[Building minihttp, the listening server](03-minihttp-server.md)** — the `socket`/`bind`/`listen`/`accept` ritual watched call by call, and the descriptor limit that quietly takes down busy servers.
4. **[The loopback interface](04-loopback.md)** — `127.0.0.1`, a network device made of software, and the irreducible cost of the kernel's stack.
5. **[Ports and /proc/net/tcp](05-ports-and-proc-net-tcp.md)** — the kernel's ledger of every socket, in little-endian hex you learn to read by hand.
6. **[TCP states and the SYN scan](05b-tcp-states-and-the-syn-scan.md)** — every state a socket moves through (`LISTEN → SYN_RECV → ESTABLISHED → … → TIME_WAIT`), and why a stealth scan that stops mid-handshake maps your ports while your app stays blind.
7. **[Everything is a file](06-everything-is-a-file.md)** — the capstone: turn the question on the `/proc` files you've trusted all act. Inodes, `mount`, and magic symlinks reveal that a "file" is an *interface* the kernel answers by running code — and the sentence the whole act circled finally gets its name.

> *Optional side road* — **[The container's filesystem is layered](06b-the-container-filesystem.md)**: the `overlay` filesystem your container's `/` runs on — copy-on-write, why `--rm` discards your changes, and how volumes keep data. Not networking, fully skippable, builds on lesson 7's `mount`.

When you've finished all seven, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *apply* it under fire — three on-call drills where you diagnose a real broken server from the symptom alone: **[Diagnose it →](diagnose.md)**. For a quick lookup of every command used in this act — and every other act's — with each syntax element broken down, see the **[command reference →](../../reference/05-per-act-commands.md)**. It lives in [the instrument panel](../../reference/README.md) now, alongside the naming grammar that lets you work out a command nobody showed you.

**What breaks here.** A machine talking to itself never has to find anyone. Loopback always knows where `127.0.0.1` is; it is itself. The socket on one end and the socket on the other end live in the same kernel, share the same `/proc/net/tcp`, and a `write()` on one becomes a `read()` on the other because the same kernel copied the bytes across — no wire, no distance, no possibility of the message being lost. The moment two separate machines must talk, every one of those guarantees evaporates. There is now a gap the kernel cannot reach across, the other machine must be *found*, and the bytes must survive a journey. That gap is Act II.
