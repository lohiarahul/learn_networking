# Act II in the wild — your real home network

The act builds two machines on a virtual bridge inside one container. This page points **the same ideas at your actual Wi-Fi**, using tools that ship with macOS. Nothing to install.

## Your neighbours on the LAN (ARP)

*Concept:* the ARP cache mapping IP → MAC is live on your Wi-Fi this second.
*(Container version: `ip neigh` on a virtual bridge.)*

- **List every device your Mac has spoken to on the LAN** — router, phone, TV, that forgotten smart bulb:
  ```
  arp -a
  ```
- **Watch a neighbour appear:** `ping <a-device-ip>` then `arp -a` again → a new IP↔MAC row.
- The first 3 bytes of a MAC are the vendor (OUI) — that's how you spot which gadget is which.

## Which Cloudflare answers you (anycast)

*Concept:* `1.1.1.1` is **anycast** — you and a friend in another city reach *different physical boxes*; longest-prefix routing picks the nearest.

- **Make Cloudflare confess its location:**
  ```
  dig CH TXT id.server @1.1.1.1 +short
  ```
  → a colo code like `"LHR"`, `"EWR"`, `"FRA"` — the actual datacenter serving you.
- **Count how few hops away it is:**
  ```
  traceroute 1.1.1.1
  ```
  → usually a handful of hops; anycast keeps the nearest copy close.

## Watch DNS happen in real time

*Concept:* one page load fans out into dozens of name lookups (ads, trackers, CDNs).

1. Terminal 1 — start a sniffer on DNS:
   ```
   sudo tcpdump -n -i en0 port 53
   ```
2. Browser — load one news site.
3. Watch dozens of strangers get resolved in a single second.

## See the packets, not just the lines (Wireshark)

*Concept:* `tcpdump` (from the ICMP/UDP lesson) prints one line per packet; **Wireshark** is that same capture *rendered* — every header field clickable, whole conversations reassembled. It's tcpdump's visual rival, and the tool you'll actually reach for the day a capture gets too dense to read by eye.

The capture tool ships with macOS; only the *viewer* is an optional install — `brew install --cask wireshark`, the one install on this page.

1. **Capture to a file** with the built-in tcpdump (`-w` = write raw packets, not text):
   ```
   sudo tcpdump -i en0 -w /tmp/cap.pcap port 53
   ```
   Load a page in the browser, then Ctrl-C.
2. **Open it in Wireshark:** `open -a Wireshark /tmp/cap.pcap`. Right-click any packet → **Follow → … Stream** to see a whole exchange as one conversation — exactly what tcpdump's line-per-packet view can't give you.
3. **No GUI? `tshark`** (installed alongside Wireshark) is its command-line form — same dissectors, same `.pcap`:
   ```
   tshark -r /tmp/cap.pcap -Y dns
   ```

Notice the shape: the `.pcap` file is the truth, and tcpdump, Wireshark, and tshark are three readers of it — the Act I reflex (*the file wins*) moved one layer out, from `/proc` to the captured packet stream.

## macOS vs Linux — the swaps this act needs

**Direct 1:1 swaps:**

| Container (Linux) | Your Mac (macOS) |
|---|---|
| `ip neigh` (ARP cache) | `arp -a` |
| `ip route` (routing table) | `netstat -rn` |
| `ip addr` (interface IPs) | `ifconfig` · `ipconfig getifaddr en0` |
| `dig` / `traceroute` / `tcpdump` | same commands (ship with macOS) |
| interface `eth0` | interface `en0` (Wi-Fi) |

**No clean 1:1 here — and why:**

- **The `ip` command itself doesn't exist on macOS** — it's Linux's iproute2. macOS kept the older BSD tools instead, so the one verb `ip` splits into three: `arp` (neighbours), `netstat -rn` / `route` (routes), `ifconfig` (addresses). Same kernel concepts, three commands instead of one.
- **`cat /etc/resolv.conf` is misleading on macOS.** The file exists but is auto-generated and often *doesn't* list the resolvers actually in use (macOS resolves per-interface, and apps mostly bypass the file). **Instead:** `scutil --dns` shows the real, per-interface resolver configuration.
