# Act XI — Knowing before someone tells you

Act X built the only thing in this course that keeps a memory on purpose. Its closing lesson gave you a record of every authorised change to the cluster, written down before anyone asked, at a cost you measured in bytes and in a fourth copy of a Secret you spent a whole lesson protecting. That record answers one kind of question extremely well: *who changed what, and were they allowed to.*

It has nothing to say about the other kind. A user got a 502 for eleven minutes yesterday afternoon, nobody made an unauthorised change, and every mechanism in the ten acts before this one would shrug if you asked what happened. `kubectl get events` forgot it an hour later — kind's own API server manifest never sets `--event-ttl`, so the one-hour default quietly applies. `kubectl logs --previous` reaches back exactly one restart. `kubectl top` has no history at all. This act is what a cluster has to do differently *before* the 502, so that the question "what happened" still has an answer when someone finally asks it.

## The idea that holds the act together

The industry's usual frame is "the three pillars: metrics, logs, traces" — three technologies, three tools to install. This course declines that frame, because it groups by product category and explains nothing about *why* there are three.

The reframe that makes it a mechanism instead of a shopping list:

```
   THE QUESTION IT ANSWERS        WHAT IT KEEPS          WHAT IT THROWS AWAY
   ------------------------------------------------------------------------
   "what did it actually say?"    every line, verbatim   nothing --
     a LOG LINE                                          and that is the bill

   "how much, how often,          the SHAPE over time    which request, which
    how slow?"                                           user, which exact line
     a COUNTER or a GAUGE

   "is it wrong NOW, and         one boolean, over        everything the query
    who do I wake?"               a window                 did not think to ask
     a RULE ON A LOOP

   "which of the twelve         the CAUSAL EDGES         almost all of it,
    was slow?"                                            on purpose, by sampling
     a SPAN WITH A PARENT

   keeps everything, fits nothing ---------> keeps almost nothing, answers one
                                              question extremely well
```

**Metrics, logs and traces are not three technologies. They are three different answers to one question: what do you keep, when you cannot keep everything?** Every one of them is a lossy compression, chosen *before* the incident, by someone who did not know what the incident would be. The incident is simply the moment that choice gets graded. And the second claim carried through the act: **every one of these costs is arithmetic you can do before you install anything** — a `grep -c` against a running API server tells you more about what you are about to buy than a vendor page does.

## The lab

The same two-node `kind` cluster you have used since Act IX, with the same kubeconfig habit:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
```

No Helm, no operator, until [in the wild](in-the-wild.md)'s closing recognition beat. Everything installed here is one container (or one hand-written Pod) with a hand-written config, and every lesson that installs something removes it again by the end.

## The lessons — read in this order

- **01 · [Nothing here remembers](01-nothing-here-remembers.md)** — where a log line actually lives, why the number in its filename is not a retention setting, and why deleting a Pod is enough to erase every word it ever wrote.
- **02 · [Copying it off the node](02-copying-it-off-the-node.md)** — a hand-written log shipper, the symlink that breaks it if you mount the wrong directory, and Loki's one design decision: index the labels, not the line.
- **03 · [A number a process keeps](03-a-number-a-process-keeps.md)** — the exposition format you have been reading unnamed since Act VI; why a counter surviving a restart is not the same trick as a gauge surviving one; and why `kubectl top` has never once asked etcd anything.
- **04 · [The loop that scrapes](04-the-loop-that-scrapes.md)** — six lines of shell that are a real time-series database, the four things missing from them, and the wall Act VII already made you diagnose once, met again from a different client.
- **04b · [The cost of one label](04b-the-cost-of-one-label.md)** — cardinality as multiplication, then as resident memory, and why the only cheap place to delete a label is before it is ever stored.
- **05 · [An alert is a loop](05-an-alert-is-a-loop.md)** — a rule's three states, why absence is not zero, and why that single distinction is the most expensive thing in this act to learn during an incident.
- **05b · [A panel is a query](05b-a-panel-is-a-query.md)** — the three parameters behind every dashboard, and why the same panel over two time ranges can honestly disagree about whether an outage happened.
- **06 · [Which request was slow](06-which-request-was-slow.md)** — a trace is one HTTP header, propagated correctly or not, and the one signal in this act that genuinely cannot exist without changing the application.

## What breaks here

**A dashboard that is flat and green because nothing is being asked, not because everything is healthy.** Prometheus pulls; a target nobody discovered produces no metric, no error and no gap — and a chart with no data looks exactly like a chart reporting a healthy zero.

**A number that is technically true and means nothing.** A p99 computed by linear interpolation inside a histogram bucket is a latency no request necessarily had; a rate computed across a Pod restart, without the one piece of logic built to catch it, is an accurate report of an impossible number.

**A control plane you can bring to its knees with one label.** Cardinality is not a budget you start at zero — an idle API server was already five figures deep before anyone typed a line of application code — and the fix has to run before a sample is stored, because after that, it is too late to be cheap.

**An alert rule that can never fire, forever indistinguishable from one that has simply never had anything to report.** A comparison against a metric that was never scraped returns nothing, not `false` — and a threshold built on `== 0` cannot see a target that quietly stopped existing.

**Two complete-looking traces for one real request.** Drop one header at one hop and a downstream service has no way to know it was ever part of anything else — the whole distributed-tracing problem, caused by one missing string.

> **The question to carry through this act:** what did this system write down before anyone asked, what did it therefore throw away, and what did keeping it cost?

---

↑ **[Course overview](../README.md)** · Prev: **[Act X — Securing the cluster](../act-10-cluster-security/README.md)** · Next: **[Nothing here remembers](01-nothing-here-remembers.md)** →
