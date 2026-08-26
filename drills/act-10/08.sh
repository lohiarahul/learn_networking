# Act X drill 8 — encryption at rest, configured and signed off
HINT='name the provider that should not have been first, or the property of the providers list that
makes its position the whole bug.'
CAUSE_SHA='689f6a627384c7dcb2dcc1487e540223e77bdf9dcd0d8be8a326eda65b0ce9a4
6dd4f4552b6535916a8f0ada9d5d1f39c60e057ea6c6e7bbd6aa9ff1fe8c4fe6
1cc987dc054a83d058d32e70bb5924254a3dca477cc334d62e0a7f843799ba39
c9f6d5c70edc909da78f016f57892ece865b48275a470abb47e5f3a35ab6833d'

# Run this while bench C is still up. The drill's closing line is the specification for this file:
# every check that would have caught the bug is a check on the *data*, not the configuration, so
# "show me the stored bytes" is the only assertion here that matters.
api_answers
NS="verify-enc-$$"
kubectl create namespace "$NS" >/dev/null 2>&1
kubectl -n "$NS" create secret generic probe --from-literal=k=canary-value >/dev/null 2>&1
RAW=$(docker exec "$CP" sh -c \
  "ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     get /registry/secrets/$NS/probe" 2>/dev/null)
kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1
case "$RAW" in
  *k8s:enc:*) ok "a Secret written now lands in etcd as k8s:enc:… — the bytes, not the config, say so" ;;
  *canary-value*) bad "a Secret written now is encrypted in etcd" \
      "the literal value is readable in the store: the first provider is still writing plaintext" ;;
  *) bad "a Secret written now is encrypted in etcd" \
      "could not read the key back from etcd at all — is bench C up and is etcdctl on the node?" ;;
esac
# The second and third parts of the fix, which the config file cannot show you: the pre-existing
# Secrets were re-written, and the key file is not world-readable.
require "the Secrets that already existed were re-encrypted, not just the new ones" \
  bash -c 'ns=kube-system; for s in $(kubectl -n $ns get secrets -o name | head -3); do
             n=${s#secret/};
             out=$(docker exec "'"$CP"'" sh -c "ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
               --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
               --key=/etc/kubernetes/pki/etcd/server.key get /registry/secrets/$ns/$n" 2>/dev/null);
             case "$out" in *k8s:enc:*) ;; *) exit 1;; esac; done'
answer_check "${ANSWER:-}"
verdict
