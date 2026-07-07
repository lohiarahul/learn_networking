# Act III — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** The initial sequence number is chosen at random rather than starting at zero. Give the two distinct things that randomness protects against.

<details>
<summary>Answer</summary>

Correctness: a delayed duplicate packet from a *previous* connection on the same four-tuple lands outside the new connection's sequence range and is discarded, instead of being mistaken for valid data. Security: an off-path attacker cannot predict the next ISN, so they cannot forge a packet (with a spoofed source address) that the server will accept — the defense against TCP sequence-number prediction the Morris worm exploited.

</details>

> **Question 2 —** When your side closes a connection first, the kernel parks it in `TIME_WAIT` for roughly 60 seconds instead of freeing it immediately. What is it protecting against, and why that particular duration?

<details>
<summary>Answer</summary>

It guards a connection that does not yet exist against a delayed duplicate packet from the connection that just died: it refuses to reuse the exact four-tuple until any stale packet still wandering the network would have expired. The duration is twice the Maximum Segment Lifetime (2×MSL ≈ 60s on Linux), long enough for any such ghost to drain from the network.

</details>

> **Question 3 —** In the handshake capture, the single line of typed text and *each* FIN cost their own packets. Why does a FIN consume a sequence number of its own, the way a SYN does?

<details>
<summary>Answer</summary>

Both SYN and FIN are control flags that mark a position in the byte stream, so each is assigned one sequence number even though it carries no data byte. That is why the closing side's final ACK acknowledges every data byte *plus one more* for the FIN — and why the data segment, each FIN, and their ACKs are all separate packets, so the full conversation costs more packets than people expect.

</details>

> **Question 4 —** `conntrack` keeps a row for a connection long after it has closed. What two tuples must each row remember, and why can't NAT work without that memory?

<details>
<summary>Answer</summary>

The *original tuple* (the source/destination addresses and ports as the packet first appeared) and the *reply tuple* (how the reply will look after translation). NAT rewrites the source on the way out, but the returning reply carries nothing saying which private host it belonged to; only the remembered mapping lets the kernel reverse the translation and deliver the reply home.

</details>

> **Question 5 —** TCP obeys two different limits on how much data it may have in flight at once. Name both, say who sets each, and say how each one reaches the sender.

<details>
<summary>Answer</summary>

The **receive window** is the receiver's ceiling — how much it is willing to buffer — and it is *told* to the sender explicitly, in the `win` field of every acknowledgement. The **congestion window** (`cwnd`) is the sender's own estimate of what the path can carry, and nothing ever tells it: no router reports its capacity, so the sender raises `cwnd` while acknowledgements keep arriving (slow start doubles it per round trip) and cuts it back when one goes missing, since a lost packet is the only signal the network sends. Bytes allowed in flight is the smaller of the two.

</details>

> **Question 6 —** Your download runs at full speed while your video call breaks up, and no packets are being lost. What is delaying the call's packets, and why does a throughput test miss it entirely?

<details>
<summary>Answer</summary>

A queue on the bottleneck link is full of the download's packets. A router absorbs a burst by queueing rather than dropping, so the call's small, urgent packets wait behind bulk data — delay, not loss. A throughput test measures how much gets through, which the queue does not reduce; it is the *waiting time* that grew. That is bufferbloat, and it appears before any packet is dropped.

</details>

> **Question 7 —** In a raw HTTP response, where exactly does the header section end, and what role does that boundary play for the parser?

<details>
<summary>Answer</summary>

A single completely blank line ends the headers; everything after it is the body. That blank line is the only separator between headers and body — it is how the parser knows the headers are done, and `Content-Length` then tells it exactly how many body bytes to read (so it knows where one response ends on a reused connection).

</details>

> **Question 8 —** HTTP/1.1 → HTTP/2 → HTTP/3 is one chain of arguments, not three fashions. State each step: the problem, the fix, and the new problem the fix exposed. Finish by saying why HTTP/3 had to abandon TCP.

<details>
<summary>Answer</summary>

HTTP/1.1 on one connection can only carry one response at a time — there is no way to label whose bytes are whose, so a slow response blocks every request behind it (head-of-line blocking); browsers worked around it by opening several connections per host, paying several handshakes and several congestion windows. HTTP/2 fixes it properly by framing the conversation in binary and tagging every frame with a stream id, so one connection interleaves many requests. But those streams still ride one TCP connection, and TCP delivers a single ordered byte stream with no gaps — it cannot know that the missing bytes belong to only one stream, so one lost segment stalls all of them. That blocking is unfixable from above, because in-order delivery is TCP's whole product. HTTP/3 therefore drops TCP for QUIC over UDP: UDP promises no ordering at all, which is precisely what makes per-stream ordering possible.

</details>

> **Question 9 —** A proxy sits in front of two servers and must send `/api/...` to one and everything else to the other. Why can a layer-4 proxy never do this, and what does the layer-7 proxy have to do differently to manage it?

<details>
<summary>Answer</summary>

A layer-4 proxy works at the level of a `/proc/net/tcp` row — source and destination addresses and ports — and forwards bytes without interpreting them. The path is not in the four-tuple; it is inside the byte stream, in the request line. So an L4 proxy can choose a backend per *connection* (next in turn, fewest connections, sticky by client IP) and check whether a backend is up, and nothing more. A layer-7 proxy terminates the connection, parses the bytes as HTTP, and opens its own separate connection to a backend — two connections instead of one relay. That is what buys it the request line, the `Host:` header, per-request retries and header rewriting, and it costs parsing, per-request state, and the requirement that it be able to *read* the bytes in the first place.

</details>

> **Question 10 —** After an `openssl s_client` handshake, what does `Verify return code: 0` actually prove — and what does it *not* prove?

<details>
<summary>Answer</summary>

It proves the server presented a certificate chain that the client verified all the way up to a root already in its trust store — i.e. a CA your machine trusts vouched for the binding between the hostname and the public key. It does *not* prove the server is honest or the site is safe; it only proves identity was vouched for and the channel is encrypted and tamper-evident.

</details>

---

← Back to **[Act III overview](README.md)** · Next: **[Diagnose it →](diagnose.md)** (apply it under fire), then **[Act IV →](../act-4-one-pretends-many/README.md)**
