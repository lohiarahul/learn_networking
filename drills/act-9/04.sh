# Act IX drill 4 — the powerless token that can see everything
HINT='name the credential that actually authenticated the request. It was in the file the whole time
and you did not pass it on the command line.'
CAUSE_SHA='ce7b638f888efc64dfb4f9796bb5810e779c7e6925ae38ff5e2bab04cab82bbd
cca9c6583c2886f47bd6c36abca2f6db138511bef41d4a4d6ac39db462c22e0f
03d66dd08835c1ca3f128cceacd1f31ac94163096b20f445ae84285bc0832d72
5f9039b4bf56cdefd3e2d319e9f7c2bc8d69e394fcda6c0e6477a24a4b0a48ae
e66e004ea4159555184da353286af25a205066e78fdc922c52b672670f8f14ef'

act9_env

# Two requests carrying the same nonsense token, differing only in what *else* they carry. That is the
# whole drill, and it is a claim about your tooling rather than about the cluster, so it is checkable
# without anything being broken.
VIA_KUBECTL=$(kubectl --token=totally-invalid auth whoami \
                -o jsonpath='{.status.userInfo.username}' 2>/dev/null)
VIA_CURL=$(api_whoami totally-invalid)
if [ -n "$VIA_KUBECTL" ] && [ "$VIA_KUBECTL" != "system:anonymous" ]; then
  ok "kubectl with a junk token still authenticates — as $VIA_KUBECTL, which is not the token's identity"
else
  bad "kubectl with a junk token still authenticates as somebody" \
      "got '${VIA_KUBECTL:-<nothing>}' — this cluster's kubeconfig may not hold a client certificate, which is the thing the drill is about"
fi
require_eq "and the same token sent on its own authenticates as nobody at all" "" echo "$VIA_CURL"
# Then the positive control: a real token, sent the same way, is believed as its own account. Without
# this the check above could pass on a broken curl.
SA=$(api_whoami "$(kubectl create token probe --duration=1h 2>/dev/null)")
require_eq "a genuine token sent the same way is believed as its own account" \
  "system:serviceaccount:default:probe" echo "$SA"
answer_check "${ANSWER:-}"
verdict
