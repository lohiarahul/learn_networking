# `curl` — "a play on *Client for URLs*"

Every byte of an HTTP(S) exchange with `-v`, plus timing breakdowns and protocol selection (`--http3`)

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [HTTP](../../../networking-fundamentals/act-3-the-internet/04-http.md) |
| **In the lab** | ✅ `/usr/bin/curl` · curl 8.18.0 (aarch64-alpine-linux-musl) libcurl/8.18.0 OpenSSL/3.5.4 zlib/1.3.1 brotli/1.2.0 zstd/1.5.7 c-ares/1.34.6 li |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `curl --help` has that. These 4 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-v` | the request and response headers — the actual conversation, rather than the body it produced |
| `-w` | timing breakdown: `time_namelookup`, `time_connect`, `time_appconnect`, `time_starttransfer`. This is what turns "it is slow" into which phase is slow |
| `--resolve` | pin a hostname to an address for this request only. Test the new server before DNS points at it, with SNI and `Host` still correct |
| `-k` | skip certificate verification. Not for production — for the diagnosis: if `-k` works, the failure was trust, not connectivity |

## What it can do

*7 commands, grouped by what you are trying to find out.*

### Every byte of an HTTP exchange

| Command | What it gives you |
|---|---|
| `curl -v https://example.com` | request and response headers, plus the TLS handshake summary |
| `curl -sS -o /dev/null -w '%{http_code} %{time_total}\n' <url>` | just the outcome and the timing |
| `curl -o /dev/null -s -w '%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer}\n' <url>` | where the time actually goes |
| `curl --resolve example.com:443:10.0.0.1 https://example.com` | override DNS without touching /etc/hosts |
| `curl --http3 <url>` | pin the protocol version; also --http2, --http1.1 |
| `curl -k <url>` | skip certificate verification — and know that you did |
| `curl --unix-socket /var/run/docker.sock http://localhost/version` | HTTP over a Unix socket |

## As the course runs it

*11 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `curl -s localhost:8080` | `curl` = HTTP client; `-s` = silent (no progress meter); `localhost:8080` = host:port | Lesson 3 — Building minihttp, the listening server |
| `curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:8080` | `-o /dev/null` = discard the body; `-w` = write out a chosen variable — `%{http_code}` is the status. The way to test reachability without reading a page | Lesson 5 — Ports and /proc/net/tcp |
| `curl --max-time 2 http://172.17.0.3:8081` | `--max-time 2` = give up after 2s, so a bound-to-loopback service fails fast instead of hanging | Lesson 5 — Ports and /proc/net/tcp |
| `curl -s google.com > /dev/null` | make and immediately finish one connection, so there is something in TIME_WAIT to look at | Lesson 2 — TCP states |
| `curl -v http://httpbin.org/get 2>&1` | `-v` prints the request and response headers — `>` lines are sent, `<` received. `2>&1` merges stderr, where `-v` writes, so it can be piped | Lesson 4 — HTTP |
| `curl -w "dns: %{time_namelookup}s\ntcp: %{time_connect}s\ntls: %{time_appconnect}s\ntotal: %{time_total}s\n" -o /dev/null -s <url>` | `-w` = write-out template with `%{variable}` fields. The cumulative timings that separate "slow DNS" from "slow TLS" from "slow server" in one command | Lesson 4 — HTTP |
| `curl -v --http1.1 -o /dev/null <url> 2>&1 \\| grep -i 'alpn\\|^> GET\\|^< HTTP'` | `--http1.1` pins the version; the grep picks out the ALPN negotiation and the request/status lines. Run against `--http2` to see the same page fetched differently | Lesson 4 — HTTP |
| `curl -sI <url> \\| grep -i 'alt-svc'` | `-I` = HEAD request, headers only; `alt-svc` is the server advertising HTTP/3 on another transport | Lesson 4 — HTTP |
| `curl -V \\| grep -o HTTP3` | `-V` (capital) = curl's **own** build info, not a request. Prints `HTTP3` only if your build supports it | Lesson 4 — HTTP |
| `curl -sI http://github.com \\| head -3` | the plain-HTTP response — a redirect, which is a request that already happened in cleartext | Lesson 5 — TLS |
| `curl -sI https://github.com \\| grep -i strict-transport` | HSTS: the header that tells a browser never to try `http://` again | Lesson 5 — TLS |
