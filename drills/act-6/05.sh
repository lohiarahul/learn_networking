# Act VI drill 5 — "we are locked out of our own cluster and nothing is down"
HINT='name the object that was deleted — the ClusterRoleBinding, as kubectl spells it.'
CAUSE_SHA='75136240e105fb3d44048f0796182cf3065ab5256d4e53ba4dd0b05ae125c299
66d0c6a286cd3b2109f5a8c00014b05088884018d0f4b6dc8dd2b1ff01ec869b'

api_answers
require "the ClusterRoleBinding is back" \
  kubectl get clusterrolebinding kubeadm:cluster-admins
# Restoring the object is not the same as regaining the access it granted. Ask the API server whether
# *this* kubeconfig can now do the thing it could not.
# `kubectl auth can-i` exits 0 for yes and 1 for no, which is what we want — its *stdout* carries a
# "resource is not namespace scoped" warning for cluster-scoped kinds that has nothing to do with the
# answer, so read the status and not the text.
require "your own kubeconfig can list nodes again" \
  kubectl auth can-i list nodes
require "and can create Pods cluster-wide" \
  kubectl auth can-i create pods --all-namespaces
nodes_ready 2
answer_check "${ANSWER:-}"
verdict
