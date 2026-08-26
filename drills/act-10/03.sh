# Act X drill 3 — the signature gate that refuses everything
HINT='the message says how far it got. Name what it could not establish to the registry, or what the
policy engine turns out to have of its own.'
CAUSE_SHA='6f3fb0b8048284ec6c2da4ff220e3d793fef27ef9ec77540010abef468065514
b7e651cbb43ba0ca3498759c8c3596c3a11a199004cd9e5a198d50d4585ec8c5
6959097001d10501ac7d54c0bdb8db61420f658f2922cc26e46d536119a31126
4e6770a13e8683160cd32043265aa68694800f147f11686c56b5995d9236c22a
56481d54f093ecbbb6d38f94ddf4f936e6a14120f33110a17491c9a1194e5d11'

# This drill is on paper — the message *is* the artifact — so unlike every other verifier in this
# repository, the answer carries almost all of the weight here, and it is worth being honest about
# that rather than inventing a state check.
#
# What is checkable is that you left the cluster as lesson 08 left it. If you reinstalled Kyverno to
# run the drill for real, its teardown line has to have been run: an admission controller left behind
# is a webhook in the write path of every Pod in the cluster, and drill 2 has already shown you what
# that costs when the thing behind it is unavailable.
note "drill 3 is a paper drill: the answer check is most of this verifier, by design."
require "no policy engine left installed — the cluster is as lesson 08 left it" \
  bash -c '! kubectl get ns kyverno >/dev/null 2>&1'
require "and no admission webhook left pointing at one" \
  bash -c '! kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations \
             -o name 2>/dev/null | grep -qi kyverno'
answer_check "${ANSWER:-}"
verdict
