# Act II drill 2 — "one particular service is unreachable; everything else is fine"
HINT='name the kind of entry that beat the default. One word about its specificity will do.'
CAUSE_SHA='a7cfdd5c713cf41856e1c5bb42a645b2ae6f838cc2576b58684b3f6ac5659ca9
8a84e406c08ac9594f47222406598f7598e15c55f8044b04813e28c9dee70976
e7edd6da7bc67389f20bdf84c95fd5c852b1585f648f209822a012f2cd9daf5a
8d0b7a9df461305d8b3d16329942f44e8376b72c80c2efc414a6902da0576cd0
d695afc1ad5384842074d4a493c7c2bebc4b0bcf8e7c6a1b45a6a0aac06d59c3'

lab_up
lab_require "8.8.8.8 answers again" 'ping -c1 -W3 8.8.8.8 >/dev/null'
lab_require "and no blackhole route is left in the table" '! ip route show | grep -q blackhole'
# `ip route get` is the check that names *which* route won, which is the skill the drill is for: the
# table is not a list you read top to bottom, it is a longest-prefix match.
lab_require "route lookup for 8.8.8.8 now resolves via the default, not a more specific entry" \
  'ip route get 8.8.8.8 | head -1 | grep -q " via "'
answer_check "${ANSWER:-}"
verdict
