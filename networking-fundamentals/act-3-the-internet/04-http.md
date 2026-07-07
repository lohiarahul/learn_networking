# HTTP

TCP hands you a reliable, ordered stream of bytes between two processes. But a stream of bytes is not a *conversation* — it has no notion of "here is a request," "here is where the reply begins," "here is how long the body is." Something has to impose structure on the stream so that a client can ask for a thing and a server can answer with that thing and know where the answer ends. The web's answer is almost shockingly simple: write the structure in plain text, with a few rules about punctuation. That is HTTP.

### Why did the web need its own protocol?

**Because a byte stream has no way to say "the request ends here" — and the web needed that boundary written in text anyone could read.**

By 1990, Tim Berners-Lee wanted documents on one machine to link to documents on another, fetched on demand. He needed a way for a browser to say "give me *this* document" and for a server to reply "here it is, and here is what kind of thing it is." It had to be trivial to implement — anyone writing a server in any language should be able to parse it — and trivial to debug by eye.

What came out was a text protocol carried over a TCP connection, and the choice of text was not an accident of taste. A binary protocol would have been faster on the wire and smaller in memory, and it would have needed a special tool before anyone could see what was happening. Text needs nothing: a socket, a keyboard, and eyes. You are about to read a complete HTTP exchange with no decoder, which is the argument for text made in one command.

### So what is HTTP, really?

**A text message written into a TCP socket, in which a single blank line is the entire boundary between headers and body.**

HTTP is a text protocol running on top of a TCP socket. The client `write()`s a formatted text message — a request — and the server `read()`s it, then `write()`s back a formatted text message — a response. The formatting is a set of *headers*: lines of `Name: value`. The request begins with a line like `GET /index.html HTTP/1.1`; the response begins with a status line like `HTTP/1.1 200 OK`. Then come the headers, one per line.

Then — and this is the load-bearing part — a single completely **blank line**, and after it, the body (the actual document). That blank line is the only thing separating headers from body; it is how the parser knows the headers have ended and the content has begun.

A `Content-Length` header tells the reader exactly how many bytes of body to expect.

### What does the conversation look like?

**Two blocks of text, each one a status or request line, then headers, then a blank line, then the body.**

One request, one response, over an established TCP connection:

<!-- figure: http-exchange -->

```
   CLIENT writes  ─────────────────────────────►  SERVER reads
   ┌───────────────────────────────────────────┐
   │ GET /get HTTP/1.1            ← request line │
   │ Host: httpbin.org           ← header        │
   │ User-Agent: curl/8.0        ← header        │
   │                             ← BLANK LINE ◄── load-bearing
   │ (no body for a GET)                         │
   └───────────────────────────────────────────┘

   SERVER writes  ◄─────────────────────────────  CLIENT reads
   ┌───────────────────────────────────────────┐
   │ HTTP/1.1 200 OK             ← status line   │
   │ Content-Type: application/json ← header     │
   │ Content-Length: 257         ← header        │
   │                             ← BLANK LINE ◄── headers end here
   │ {                                           │
   │   "args": {},               ← body,         │
   │   ...                          exactly 257  │
   │ }                              bytes        │
   └───────────────────────────────────────────┘
```

### Where do you read HTTP's bytes?

**There is no file — HTTP *is* the bytes in the socket, and `curl -v` prints both directions as a transcript.**

HTTP has no `/proc` file of its own; it *is* the bytes flowing through the socket file. The way to read those bytes is to ask `curl` to print them:

```bash
curl -v http://httpbin.org/get 2>&1
```

In the output, every line beginning `> ` is a byte the client *sent*; every line beginning `< ` is a byte the server *returned*. (Lines beginning `* ` are curl's own commentary — DNS, connection — not part of HTTP.)

Read it as a transcript: the `> GET /get HTTP/1.1` line and the `> Host:` lines are your request; the blank `> ` line is the load-bearing separator ending your headers. Then `< HTTP/1.1 200 OK`, the `< ` headers, the blank `< ` line ending the server's headers, and finally the body. Find the `< Content-Length:` header, note its number, and count: the body that follows is exactly that many bytes. That is the entire protocol, visible as text.

> **Check yourself —** A server sends its status line and headers but forgets the blank line before the body. What does the client do?

<details>
<summary>Answer</summary>

It keeps reading the body as more headers. The blank line is the *only* thing that terminates the header section, so without it the parser has no boundary — it will either wait for headers that never end or treat your JSON as a malformed header. This is why the blank line is described as load-bearing rather than cosmetic.

</details>

### How many stages does one fetch really take?

In `docker run --rm -it --privileged --network host --name lab nicolaka/netshoot`, break a single HTTPS fetch into its timed stages:

> **Predict first —** a single `curl` looks like one event; how many distinct stages does it actually pass through before the first byte of the page arrives, and which one do you expect to dominate?

```bash
curl -w "\n--- timing ---\ndns:   %{time_namelookup}s\ntcp:   %{time_connect}s\ntls:   %{time_appconnect}s\ntotal: %{time_total}s\n" -o /dev/null -s https://google.com
```

The surprising, clarifying result: a single `curl` is not one event but four, and `curl` times each cumulatively from the start. `time_namelookup` is when DNS finished. `time_connect` is when the TCP three-way handshake (Act III's first concept) completed. `time_appconnect` is when the TLS handshake (next chapter) completed. `time_total` is when the last byte arrived.

Subtract adjacent numbers and you get the *duration* of each stage: TLS took `appconnect − connect` seconds, transfer took `total − appconnect`. Now any slow HTTPS request stops being "the internet is slow" and becomes "DNS was fine, TCP was fine, but TLS took 800ms" — a specific, fixable diagnosis.

### Why does one connection make a fast page slow?

Hold on to those four stages, because they are a *bill*, and the early web paid it per document.

HTTP/1.0 closed the TCP connection after every single response — one handshake, one document, goodbye — so a page with thirty images paid thirty handshakes, and once TLS existed, thirty TLS handshakes on top. HTTP/1.1 fixed the obvious half of that with **Keep-Alive**: leave the connection open and send the next request down the same pipe. Pay the handshakes once, reuse them forever. There is a second, quieter saving the reliability lesson taught you to see: a fresh connection starts with a congestion window of about ten segments and has to earn its way up, so every new connection is not just slow to open, it is slow to *go fast*. Reusing one keeps the sender's hard-won guess about the path.

Now find the wall. One connection, thirty requests — in what order do the responses come back?

They come back in the order they were asked for, and each one must *finish* before the next begins. There is nowhere to put an answer that says "this is a piece of response number 4." (HTTP/1.1 does let a client fire several requests off without waiting — *pipelining* — but the responses still have to arrive in the order they were requested, for exactly that reason, so it bought almost nothing and browsers turned it off.) The stream is a single ordered run of bytes and the only structure in it is `Content-Length`, which tells you where a response ends — so the next response cannot start until the previous one has run its full length. If request 1 is a slow database query and requests 2 through 30 are small images sitting in cache, all twenty-nine wait behind it. That is **head-of-line blocking**: one slow item at the front stalls everything behind it, not because the network is busy but because the protocol has no way to label whose bytes are whose.

Feel the serial floor. Six requests to the same host, down one connection:

```bash
time curl -s --http1.1 \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/ \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/ \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/
```

Now let curl open a connection per request instead, all at once (`--parallel` needs curl 7.66 or newer; `curl -V` prints your version):

```bash
time curl -s --http1.1 --parallel \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/ \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/ \
  -o /dev/null https://www.cloudflare.com/ -o /dev/null https://www.cloudflare.com/
```

Your milliseconds are your own; the ratio is the point. Serial costs roughly six times one request, and the parallel run collapses toward the cost of the slowest single one. This is exactly the workaround the whole web adopted: browsers opened around six connections per hostname and sprayed requests across them, and web developers "sharded" assets across extra hostnames to buy more. Look at what that costs — six handshakes, six TLS handshakes, six congestion windows each starting from scratch and competing with the other five for the same bottleneck — all to work around a protocol that cannot say "this byte belongs to request 4."

### Can one connection carry many requests at once?

That is the question HTTP/2 exists to answer, and the answer required giving up the one thing HTTP was famous for.

HTTP/2 replaces the text on the wire with a **binary framing layer**. The conversation is still request line, headers, body — you have not lost the model you just read — but it travels as *frames*, and every frame carries a **stream identifier**. That single number is the label HTTP/1.1 lacked. Now one connection can carry frames of stream 1 and stream 7 interleaved, in any order, and the receiver sorts them out by id. Thirty requests, one connection, all in flight at once. Headers get compressed too (the same `User-Agent` and `Cookie` repeated thirty times is pure waste).

Which raises a practical problem the reader of a plain-text protocol should immediately feel. Text is forgiving: a server that gets a request it does not understand can answer in words. Binary is not. If the client speaks frames to a server that only knows text, or text to a server expecting frames, nobody can even produce an error — and the client has to choose *before* it sends its first byte. Both sides must therefore already agree on the language when HTTP begins, which means the agreement cannot be made in HTTP.

So watch where it gets made instead.

> **Predict first —** you are about to run the same fetch twice, once with `--http1.1` and once with `--http2`. The version used will differ, obviously. Write down *where in the output* you expect the decision to be visible: in the request line the client sends, or somewhere before it — and if it is before, whose turn was it to speak?

```bash
curl -v --http1.1 -o /dev/null https://www.cloudflare.com/ 2>&1 | grep -i 'alpn\|^> GET\|^< HTTP'
curl -v --http2   -o /dev/null https://www.cloudflare.com/ 2>&1 | grep -i 'alpn\|^> GET\|^< HTTP'
```

(If `--http2` is rejected outright, your curl was built without it — `curl -V` lists a `HTTP2` feature when it is present.)

Read the two outputs side by side. The request lines differ as expected — `GET / HTTP/1.1` and `HTTP/1.1 200` versus `GET / HTTP/2` and `HTTP/2 200`. But the decision is not there. It is on the `ALPN` lines, which come *first*: one side offers a list of protocol names and the other accepts one — `http/1.1` alone in the first run, `h2` accepted in the second. `h2` is the name of HTTP/2 on the wire. So the language was settled before a single HTTP byte moved, and the machinery that settled it is not HTTP.

Where did that conversation happen? Look at the surrounding `curl -v` output and you will see it sits inside the phase you timed as `time_appconnect`. Both endpoints were already exchanging setup messages there for a completely different reason, and this negotiation rode along inside them at no extra cost — no guessing, no wasted round trip, nothing added to HTTP at all. The extension is called **ALPN** (Application-Layer Protocol Negotiation). *How* that phase has room to carry a list of protocol names, and who is allowed to speak in it, is the next lesson's business — take the observation now and hold the question. Note also what did *not* change between the two runs: the method, the path, the headers, the status code. HTTP/2 changed the encoding and the multiplexing, not the conversation.

### What is HTTP/2 still stuck behind?

Multiplexing thirty streams over one connection solves HTTP's head-of-line blocking. Now ask where those thirty streams actually live.

They live in **one TCP connection** — and TCP's central promise, the one you spent a whole lesson on, is a single ordered byte stream. TCP hands bytes to the application *in order, with no gaps*, and it has no idea that byte 4,000 belongs to stream 1 and byte 5,000 belongs to stream 7. So when one segment is lost, TCP holds back everything that arrived after it until the retransmission lands. Every stream stalls, including the twenty-nine that had nothing to do with the missing bytes.

Head-of-line blocking did not disappear. It moved down a layer, from HTTP to TCP — and there it is *unfixable from above*, because in-order delivery is not a bug in TCP, it is the product. You cannot ask TCP for "in order per stream" when TCP has never heard of streams.

Which leaves exactly one way out: stop using TCP.

Look back at Act II for a moment. UDP was the bare datagram — no handshake, no ordering, no retransmission, no connection at all, just "here is a packet, good luck." It looked like the poor relation, TCP with the useful parts removed. It is now the only foundation on which per-stream ordering is *possible*, precisely because it imposes no ordering of its own. Where TCP hands you a promise you cannot renegotiate, UDP hands you a blank sheet.

**HTTP/3** takes that sheet. It runs over **QUIC**, a transport built on UDP that reimplements — per stream, in the program rather than the kernel — everything TCP does: sequence numbers, acknowledgements, retransmission, congestion control, and the handshake, with the encryption built into the transport rather than bolted above it. A lost packet now stalls only the stream whose bytes were in it. Every other stream keeps delivering.

That is the whole chain, and it is one argument end to end: HTTP/1.1's head-of-line blocking motivated HTTP/2's multiplexing; HTTP/2's TCP-level blocking motivated HTTP/3 over QUIC; and QUIC needs UDP because UDP is the only transport that promises little enough.

One more thing falls out of it, and you can work it out yourself from something you already own. A TCP connection *is* its four-tuple — you read that row out of `/proc/net/tcp`, and both kernels index their state by exactly those four numbers. So: your phone is halfway through a download and walks out of Wi-Fi range onto cellular. Its IP address changes. What happens to every connection it had, and why is there nothing TCP could do about it? Now ask what a transport would have to identify a connection *by*, if it wanted to survive that. QUIC gives each connection an ID of its own, independent of any address. Sit with why that is only possible for a transport that was not built around the four-tuple in the first place.

You can see the offer whether or not your curl can take it up. Every HTTP/3-capable server advertises the fact in an ordinary HTTP header over its ordinary HTTPS connection:

```bash
curl -sI https://www.cloudflare.com/ | grep -i 'alt-svc'
```

(`-I` asks for the headers only — the same request line you have been reading, with the method `HEAD` in place of `GET`, so the server sends its headers and no body.)

The `alt-svc` header names alternative services for this origin, and an entry beginning `h3=` is the server saying "I also speak HTTP/3 on this port, come back over QUIC next time." That is how browsers find HTTP/3 at all: over TCP first, then upgrade. (Not every server advertises it, and some send it only on certain responses — if you get nothing, try another large HTTPS site.) To try it directly you need a curl built with HTTP/3, which many are not:

```bash
curl -V | grep -o HTTP3        # prints HTTP3 if your build has it, nothing if not
curl -sI --http3 https://www.cloudflare.com/ | head -1      # only if the line above printed
```

If it prints nothing, you have lost nothing conceptually — the `alt-svc` header is the observation that matters, and it is there either way.

### What can a machine in the middle decide?

Here is a job to do, and it is an ordinary one. You have one public address and one port. Behind it are two servers: requests whose path starts `/api/` must reach the first, everything else must reach the second. Clients know nothing about any of this — they open one connection to one address, exactly as you have been doing all lesson. Something in the middle has to decide which server each request belongs to.

Try it with what a connection gives you. A connection, as you have read it straight out of `/proc/net/tcp`, is four numbers and a state: source address, source port, destination address, destination port. Stare at that row and find `/api` in it.

It is not there. It never was. The path lives in the first line of the request, which is *inside* the byte stream — and a machine can forward a byte stream perfectly without ever looking at one byte of it. Two entirely different depths of involvement, then, and it turns out everything a middlebox can do follows from which one it chose.

A **layer-4 proxy** lives at the depth of that `/proc/net/tcp` row. It accepts a connection, opens one to a backend, and shovels bytes between them without interpreting a single one (or it goes shallower still and merely rewrites addresses on packets — that is NAT, and Act IV's business). Its whole world is the four-tuple:

```
   what an L4 proxy knows          what it can therefore decide
   ──────────────────────          ────────────────────────────
   source IP, source port          which backend gets this connection
   dest IP, dest port              — pick the next one in turn, or the
   bytes in, bytes out               one with fewest connections, or
   the connection is up/down          always the same one for a given
                                      client IP (so a session sticks)
   ── and nothing else ──          whether a backend is up
                                   it cannot route on a path. it has
                                   never seen one, and never will.
```

A **layer-7 proxy** goes deeper: it *terminates* the connection, reads the bytes as HTTP, and opens its own separate connection to a backend. Two connections, not one relay. Now it holds the request line and every header, so it can do your job — `/api/*` here, `/static/*` there — and more besides: route twenty different sites off one address by reading the `Host:` header, retry a failed request on another backend (it knows where the request ended, so it can send the same one again), add or strip headers, and keep its own pool of reused connections to backends regardless of how clients connect to it.

The costs line up one-for-one against those abilities. The L4 proxy is cheap, keeps almost no state, and will carry anything TCP carries — a database protocol, an SSH session, something invented next year — because it never needed to understand any of it. The L7 proxy must parse every request, holds state per request rather than per connection, costs two connections instead of one, and — the sharp one — **must be able to read the bytes**.

That last cost is worth stopping on, because over plain HTTP it is free and you have already proved it: you read a complete request and response as text, with no tool but `curl`. Over `https://` you have not yet looked at what the `s` changes. So carry the question rather than the answer: if routing on a path *requires* reading the request line, what does that tell you about what the `s` must be doing to those same bytes — and what would a middlebox have to be handed before it could read them anyway? That is exactly the next lesson's subject. Notice the shape of the trade before you know its mechanism: the deeper a middlebox reaches, the more it has to be trusted with.

One more question to carry, and it is the reason this section exists. Kubernetes has two different objects for getting outside traffic to a Pod, and one of them cannot route on a URL path no matter how you configure it. Which is which — and what must the other one have been handed in order to do its job?

> **You understand this when you can** take one `curl -v` transcript, point at the single line an L4 proxy could route on and at the `>` and `<` lines an L7 proxy would need instead, and say which of the two could implement `/api` routing and which could not and why — then point at the `ALPN` line, name the protocol it settled on, and say why that decision could not have been made in HTTP itself.

### What will this ask of you in a cluster?

Three things you now know how to look at, held as questions rather than conclusions.

**First:** a health check is a machine writing `GET /healthz HTTP/1.1` into a socket and reading the status line — nothing you have not done by hand. So who writes it in a cluster, and what should it do differently when the status line comes back as an error (the server answered, and said it is unwell) versus when nothing comes back at all? **Second:** routing on the `Host:` header requires reading the `Host:` header, and reading it over HTTPS requires the certificate. Where in a cluster does the certificate have to live, then, and what does that mean for the traffic *after* that point? **Third:** you just measured what a fresh connection costs — handshake, TLS, a congestion window starting from ten segments. Multiply that by every request between every pair of components. What single setting is therefore worth the most, and what breaks if a middlebox reuses connections and something behind it disappears?

Act V settles all three. You can predict the shape of each answer already, which is the point.

> **On your own machine —** run this exact four-stage timing breakdown against a site you open every day, twice in a row, and see where your latency actually lives — and why the second load is so much faster — in [Act III in the wild](in-the-wild.md#where-your-latency-lives-http-timing).

---

← Prev: **[TCP and reliability](03-tcp-reliability.md)** · ↑ **[Act III overview](README.md)** · Next: **[TLS](05-tls.md)** →
