# Act V drill 4 — "it hangs for thirty seconds and nothing is logged anywhere"
HINT='name the kind of object that arrived with the config changes, or what it did to every
Pod in the namespace the moment it selected them.'
CAUSE_SHA='21d4bf7194699a2867485b4b26636ea76c4a5efad9219219bd50253e57762f18
106b0db68279044c56565fe837c90aef4693ec5983db139c2bdb4a4ff2974c75
2f8b14ad84f4c0e1942de2af7d1c8c7ac3f0b5dd512d0b6a8e6587957adac8ae
308258b060c17ab9d17a47fddb4e1acc4546246373157fd0384b61a1b5516d50
41eb8d810401132208eb8a03961d8817b32d5d301623f66b0e42da46742af181'

# Run this *before* the Cleanup line. `svc_answers` names its Pod `probe`, so it wears `run=probe` —
# the same label the drill's own probe Pod wears, and the one the reveal's allowance permits.
endpoints_ready drill4 db 1
svc_answers drill4 db
# The anti-cheat, and the whole lesson: deleting the baseline policy also makes the curl work, and it
# is the wrong fix. A default-deny plus a named exception is the shape you were asked for, so both
# halves have to be present — something must still isolate these Pods for Ingress.
require "a NetworkPolicy still isolates the db Pods (you added an exception, you did not delete the deny)" \
  bash -c 'kubectl -n drill4 get networkpolicy \
             -o jsonpath="{range .items[*]}{.spec.policyTypes}{\"\n\"}{end}" | grep -q Ingress'
require "and the drill left no hang Pod looping in the background" \
  bash -c '! kubectl -n drill4 get pod hang >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
