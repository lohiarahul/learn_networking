# Act III in the wild — your real internet connection

The act turns lossy packets into a dependable, then private, conversation. This page measures **the same forces on your own line**, using tools that ship with macOS. Nothing to install.

## Distance, measured in milliseconds (speed of light)

*Concept:* RTT is a ruler. Light in fibre ≈ **200 km per millisecond**.

- ```
  ping -c 5 1.1.1.1
  ```
- Take the avg RTT → rough one-way distance ≈ `RTT/2 × 200 km`.
  - 20 ms RTT ≈ ~2,000 km of cable round-trip. A 150 ms server is *physically* far — no upgrade beats the speed of light.

## Why your call stutters mid-download (bufferbloat)

*Concept:* a fat download fills a buffer; your call's packets wait in that queue. "Fast" speed tests miss it.

- ```
  networkQuality -v
  ```
  - Reports **responsiveness (RPM)** idle vs under load. Watch RPM crater when loaded → that drop *is* bufferbloat.

## Where your latency lives (HTTP timing)

*Concept:* a single request is layers stacked — DNS → TCP → TLS → server think-time. Time each.

1. Run this against a site you open daily:
   ```
   curl -w "dns:    %{time_namelookup}s\ntcp:    %{time_connect}s\ntls:    %{time_appconnect}s\nttfb:   %{time_starttransfer}s\ntotal:  %{time_total}s\n" -o /dev/null -s https://example.com
   ```
2. **Run it twice.** Second run: `dns` ≈ 0 (the answer is cached), `tls` and `total` drop — the caches are warm. That's *why* the second load feels instant.
   - `dns` = Act II · `tcp` = Act III handshake · `tls` = encryption setup · `ttfb` = the server thinking.

## macOS vs Linux — the swaps this act needs

**Direct 1:1 swaps:**

| Container (Linux) | Your Mac (macOS) |
|---|---|
| `ping` | `ping` (same; `-c` count works) |
| `curl -w` | `curl -w` (identical) |

**Where there's no 1:1 — and why:**

- **`networkQuality` is the reverse case: macOS has it, Linux doesn't.** It's an Apple built-in (Monterey+) with no default Linux equivalent. So this is the one place the Mac hands you *more*, not less — enjoy it; there's nothing to swap.
- **Reading the live congestion window / socket internals** (Linux's `ss -i`, which prints `cwnd`, RTT, retransmits per socket) **can't be done on macOS** — there's no `/proc` and no `ss`. **Instead:** infer the same behaviour from the *outside* with `ping` (RTT) and `networkQuality` (queueing under load), rather than reading the kernel's per-socket counters directly.
