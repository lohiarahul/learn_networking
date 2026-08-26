# `tshark` — terminal shark

The same bytes `tcpdump` captures, but *dissected* — Wireshark's protocol decoders, so you read named fields instead of hex

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags + *filter* |
| **Mode** | live |
| **Taught in** | [Act II in the wild](../../../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| **In the lab** | ✅ `/usr/bin/tshark` |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `tshark --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-Y` | a **display** filter — Wireshark's grammar, applied after dissection, so it can match `http.request` and other things libpcap has never heard of |
| `-e <field>` | with `-T fields`, print named fields only. This is what makes a capture into columns you can feed to `sort` and `awk` |
| `-z` | a statistics tap — `conv,tcp` for a conversation table, computed over the whole capture rather than per packet |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### tcpdump's bytes, dissected into named fields

| Command | What it gives you |
|---|---|
| `tshark -i <dev> -n` | live, with Wireshark's protocol decoders |
| `tshark -r cap.pcap -Y 'http.request'` | -Y is a display filter — fields, not bytes |
| `tshark -r cap.pcap -T fields -e ip.src -e tcp.dstport` | extract named fields as columns |
| `tshark -r cap.pcap -z conv,tcp` | conversation statistics |
