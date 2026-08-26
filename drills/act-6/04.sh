# Act VI drill 4 — "same symptom, and this time crictl shows nothing"
HINT='one word: the step the kubelet never got past. Drill 3 got further than this one did.'
CAUSE_SHA='30c471f6aafbca7085640653eeef555e85eb0df1602c98a662814c27767d1188
eb6f099bdeb88ec0ef12af693078f81b192829083906415e739085501277618f
9831daaaa0a94144fc3378fde30109ecfc1639ae1d738f35bedbb6ac80210f85
a52e6a56b0ff166fd6f18f6b6b25dea40c7b413b312b7e9589331f44689b89e4'

api_answers
all_static_manifests
control_plane_pods_ready
# The distinguishing fact of this drill: a manifest that does not parse produces no container at all.
# So require that one *does* now exist, from the runtime's own ledger rather than from the API server.
require "the runtime has a kube-apiserver container (crictl, not kubectl)" \
  docker exec "$CP" sh -c 'crictl ps --name kube-apiserver -q | grep -q .'
# A kind node has no python3, so do not try to parse the YAML here — the runtime already answered
# that question. A manifest that does not parse produces no container, and the check above found one.
# What is left is the debris: the two lines the drill appended must be gone from the file itself.
require "no injected garbage left in the kube-apiserver manifest" \
  docker exec "$CP" sh -c '! grep -qE "^\s*- --oops|^\s*bad: \[" /etc/kubernetes/manifests/kube-apiserver.yaml'
nodes_ready 2
answer_check "${ANSWER:-}"
verdict
