# Act I — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** A busy server stops accepting new connections even though CPU and memory are fine. Why does running out of file descriptors stop it from talking to the network at all?

<details>
<summary>Answer</summary>

A socket *is* a file descriptor, so it lives in the same per-process fd table as files and pipes. When that table hits its ceiling, `socket()` and `accept()` fail with "too many open files" (`EMFILE`) — the resource that ran out is table rows, not CPU or memory.

</details>

> **Question 2 —** `socket()` returns a small integer. What does that integer actually index, and in what sense is a socket "just a file"?

<details>
<summary>Answer</summary>

It indexes a row in the kernel's private per-process fd table, where the kernel holds the real object. The socket is "just a file" because once a connection exists, the same `read()` and `write()` verbs work on it as on any file — the integer is indistinguishable from a file's descriptor.

</details>

> **Question 3 —** You have a socket's inode from a row in `/proc/net/tcp`. How do you find which process owns it, and why does that link exist?

<details>
<summary>Answer</summary>

Grep the inode across `/proc/*/fd` (whose symlinks read `socket:[inode]`); the match names the owning process. The link exists because the row in `/proc/net/tcp` and the descriptor in `/proc/<pid>/fd` are two views of one kernel object, joined by the inode number.

</details>

> **Question 4 —** Why can only root `bind()` to ports 0–1023, and what does that rule buy you when you connect to port 22?

<details>
<summary>Answer</summary>

The kernel refuses to let a non-root process claim a low port, so "answering on port 22" can only mean a privileged program — that enforced contract is what lets "this is SSH" or "this is HTTPS" mean something rather than being an unprivileged impostor.

</details>

> **Question 5 —** Your process holds only the integer `4` for a socket. Name the three things the *kernel's* socket object behind that integer holds — and say what `write()` and `read()` actually do, given those.

<details>
<summary>Answer</summary>

The kernel object holds the connection's **identity (the tuple** of local IP:port + remote IP:port), its **two buffers** (a send queue and a receive queue), and its **state** (`LISTEN`/`ESTABLISHED`/…). Given those, `write()` only *copies bytes into the send buffer* and `read()` only *pulls bytes out of the receive buffer* — neither touches the wire; moving bytes on and off the wire is the kernel's job.

</details>

> **Question 6 —** `fd-demo` ran `socket()` and its socket had an inode, yet it never appeared in `/proc/net/tcp`. minihttp's socket did. What one step makes the difference?

<details>
<summary>Answer</summary>

`bind()`. fd-demo's socket was never given an address, so it had no identity and earned no row; `bind()` (which minihttp runs) claims a local address and port, and only an addressed socket appears in `/proc/net/tcp`.

</details>

> **Question 7 —** Name the three states a server socket moves through during a successful connection setup, and say which one makes `accept()` return.

<details>
<summary>Answer</summary>

`LISTEN → SYN_RECV → ESTABLISHED`. `accept()` returns only when the socket reaches **ESTABLISHED** — i.e. after the client's final ACK completes the three-way handshake. The arriving SYN (which moves the socket to SYN_RECV) and the outgoing SYN-ACK happen entirely in the kernel; the application is woken only at the last step.

</details>

> **Question 8 —** An `nmap` SYN scan reports your port 8080 as `open`, but your application's logs show no connections at all. How can both be true — and where would you have to look to detect the scan?

<details>
<summary>Answer</summary>

A SYN scan does only SYN → SYN-ACK, then sends a RST instead of the final ACK, so the connection never reaches ESTABLISHED. The kernel's SYN-ACK reply already proves the port is open (nmap's verdict), but because `accept()` fires only at ESTABLISHED, the application is never handed a socket and logs nothing. To detect it you have to drop below the application — to the kernel/network layer (firewall logs, `conntrack`, an IDS), which saw the SYN itself.

</details>

> **Question 9 —** `stat /proc/net/dev` reports `Size: 0`, yet `cat /proc/net/dev` prints a full table that changes every time you read it. How is a zero-byte file not empty — and what does that tell you a "file" fundamentally is?

<details>
<summary>Answer</summary>

`/proc` is a *virtual* filesystem (`type proc`, no disk behind it — `df` shows size 0). Its files store no bytes; reading one makes the kernel **run a function** that builds the answer from live state (here, the current interface counters) right then. So the size is 0 because nothing is stored, but there's always fresh content because it's computed on read. The deeper point: a "file" is not bytes-on-a-disk, it's an *interface* — anything that implements the read/write operations the VFS exposes. Stored bytes are just one way to answer; `/proc` answers with code.

</details>

> **Question 10 —** You open a file on fd 7, then `rm` its only name. `ls /tmp` no longer shows it, but `cat /proc/self/fd/7` still prints its contents. Why does the data survive — and what is it about an inode that makes this work?

<details>
<summary>Answer</summary>

A name is only a pointer to an **inode**, which is the real file (it owns the bytes and a *link count* of how many names point at it). `rm` removes one name and drops the link count, but your open fd is also a reference; the kernel frees the inode's data only when link count *and* open references both hit zero. So with fd 7 still open the inode lives on with no name, and `/proc/self/fd/7` (a magic symlink shortcutting straight to the open-file object) still reads it. This is exactly how responders recover a deleted-but-still-running binary.

</details>

---

← Back to **[Act I overview](README.md)** · Next: **[Diagnose it →](diagnose.md)** (apply it under fire), then **[Act II →](../act-2-two-machines/README.md)**
