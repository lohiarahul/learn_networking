# Act I in the wild — your Mac's live socket table

The act runs inside a throwaway Linux container so you can break things safely. This page does the opposite: it points **the same idea at the machine in front of you**, using tools that already ship with macOS. Nothing to install.

*Concept:* the live socket table — every program quietly holding a connection — and who's eating your bandwidth.
*(Container version: `ss` + `/proc/net/tcp` + `/proc/<pid>/fd`.)*

- **Who's listening on your Mac (servers):**
  ```
  lsof -nP -iTCP -sTCP:LISTEN
  ```
  - `-n` no DNS lookups, `-P` no port-name lookups → raw numbers, fast.
  - Read the columns: `COMMAND  PID  USER  FD  ...  NAME` → `NAME` is `addr:port`.
- **Live connections right now:**
  ```
  lsof -nP -iTCP -sTCP:ESTABLISHED
  ```
- **The bandwidth hog (bytes per process, live):**
  ```
  nettop -P
  ```
  - `-P` = per-process rollup; watch `bytes_in` / `bytes_out` climb. Quit with `q`.

## macOS vs Linux — the swaps this act needs

**Direct 1:1 swaps:**

| Container (Linux) | Your Mac (macOS) |
|---|---|
| `ss -ltnp` (listeners) | `lsof -nP -iTCP -sTCP:LISTEN` |
| `ss -tnp` (established) | `lsof -nP -iTCP -sTCP:ESTABLISHED` |
| `lsof -p <pid>` | `lsof -p <pid>` (identical) |

**No 1:1 here — and why:**

- **`cat /proc/net/tcp` / `cat /proc/<pid>/fd`** — *can't be done on macOS.* macOS's kernel (XNU/BSD) never adopted Linux's `procfs`, so the kernel's socket table simply isn't exposed as a file you can `cat`. The whole Act I move of *reading the raw kernel ledger by hand* has no equivalent. **Instead:** `lsof` asks the kernel the same question through syscalls and reconstructs the view — you get the `COMMAND`, PID, and `FD` (e.g. `3u` = fd 3, read+write — the minihttp fd), just not as a literal file.
- **`ss`** — *doesn't exist on macOS* (it's part of Linux's iproute2). **Instead:** `lsof -i` (to name the owner) or `netstat -an` (to count sockets).
- **The `netstat` trap:** on Linux `netstat -p` / `ss -p` means *show the process*; on macOS `netstat -p` means *protocol* (`netstat -p tcp`) — macOS `netstat` will **never** name the program behind a socket. **So:** `netstat` to *count*, `lsof` to *name*.
