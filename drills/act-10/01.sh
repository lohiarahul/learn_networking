# Act X drill 1 — the rollback that changed nothing
HINT='name the field that would have told you what actually ran, or name the property of the
reference that made the rollback a no-op.'
CAUSE_SHA='b8fbf8ac4ad0a9776e14d37b96643b66f4a994d398494bf1c34c5f7f327bf3a0
0bf474896363505e5ea5e5d6ace8ebfb13a760a409b1fb467d428fc716f9f284
2f48feb47a8ae05117f7c10ed4a0ffc1c3ef6b052c444170e9b973469f0e585f
d156b6f4db85f8dd26ac0cb9c713a215b1f345cbd854af02fc71a4116d42f8dd
094f4268a73fbce28ec06922a3d0e7b7e02b64b5b24d6ad3878d2fad35bb625c
539d13a5ce0e9ff517349a00941c1906f1de6858912e01ac5df0bf015a9eea2a'

# Run this while bench A is still up, before the teardown block.
#
# The check is the drill's own answer turned into an assertion: three Pods, one image string, and the
# only field that says what ran is `status.containerStatuses[].imageID`. If those three digests are all
# the same, the drill did not reproduce — most likely the re-push failed quietly, which is the trap the
# drill's own `crane digest` line exists to catch.
require "all three of the drill's Pods are there to be compared" \
  bash -c 'for p in d1a d1b d1c; do kubectl -n drill get pod $p >/dev/null 2>&1 || exit 1; done'
require "the three Pods do *not* all share one imageID — one spec string ran two different programs" \
  bash -c 'n=$(kubectl -n drill get pod d1a d1b d1c \
                 -o jsonpath="{range .items[*]}{.status.containerStatuses[0].imageID}{\"\n\"}{end}" \
               | sort -u | grep -c .); [ "$n" -ge 2 ]'
require "and d1b — the IfNotPresent one — is the odd one out, not d1c" \
  bash -c 'a=$(kubectl -n drill get pod d1a -o jsonpath="{.status.containerStatuses[0].imageID}");
           b=$(kubectl -n drill get pod d1b -o jsonpath="{.status.containerStatuses[0].imageID}");
           c=$(kubectl -n drill get pod d1c -o jsonpath="{.status.containerStatuses[0].imageID}");
           [ "$a" = "$b" ] && [ "$b" != "$c" ]'
answer_check "${ANSWER:-}"
verdict
