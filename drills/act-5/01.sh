# Act V drill 1 — "one new Pod can't reach anything by name"
HINT='name the Pod-spec field that was set, or the value it was set to. It is one line, and it is
not in the network.'
CAUSE_SHA='5f2153fade2724013841b0d4f765ff88d2b0b6a2238c7678e68d048a8ba1b854
d57875a2fe80a0c07f43cd31fa835156917aca60c76153d8da8acc06a4a0e263
b366f0402358d999c25ed9033b38a7408f86ff99c45cf214176cc8358de1ada1
1dc3af81b5bc819dfa1360be4ca5f6c959a74e9bd79447d00337f7891d82723f'

# Run this *before* the Cleanup line — everything it checks lives inside namespace drill1.
#
# The Pod has to be recreated, not patched, so a passing check must not simply be "a Pod named client
# exists". It must be a client that resolves. And the field is immutable for a reason worth checking
# separately: /etc/resolv.conf is written once, at sandbox creation, so the *file* is the evidence.
pod_ready drill1 client
require "the client's /etc/resolv.conf now names the cluster resolver, not the node's" \
  bash -c 'dns=$(kubectl -n kube-system get svc kube-dns -o jsonpath="{.spec.clusterIP}");
           kubectl -n drill1 exec client -- grep -q "nameserver $dns" /etc/resolv.conf'
require "and it carries a cluster search list, so a bare Service name expands to something" \
  bash -c 'kubectl -n drill1 exec client -- grep -Eq "^search .*svc\.cluster\.local" /etc/resolv.conf'
# Function, not configuration: the file can be right and the resolver still unreachable.
require "the client resolves web by name and gets an answer" \
  bash -c 'kubectl -n drill1 exec client -- curl -sSf -m 8 -o /dev/null http://web/'
answer_check "${ANSWER:-}"
verdict
