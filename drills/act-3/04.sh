# Act III drill 4 — "timeouts under load, and they clear when traffic dies down"
HINT='name the table that filled up. It is the one that makes a stateless filter stateful.'
CAUSE_SHA='8791d2e0069ac71d2f62a61f288b5009b67bcbabcddd1224d0cff0dc57a1f5ef
637af8b92c9bd76d394bba54077056dbcc32fba60dee35f10e1026fc48859d86
51c62ae9186f253dc384a8dc8b50311af7a422af836a72edb0bbdcb8e471a2c0
0b8ed08716c40d3c15ebe9bcbd897a1fa01900ac78fe52b75c4ff23961f321fe'

lab_up
# The drill deliberately saved the original value to /tmp/ct_max_before, so "restored" means restored
# to *that*, not to a number this file happens to think is normal.
lab_require "nf_conntrack_max is back to the value the drill saved before touching it" \
  'want=$(cat /tmp/ct_max_before 2>/dev/null | tr -d " ");
   have=$(cat /proc/sys/net/netfilter/nf_conntrack_max);
   if [ -n "$want" ]; then [ "$have" = "$want" ]; else [ "$have" -ge 4096 ]; fi'
# And the pair of numbers the drill says to read together — count against max — with headroom.
lab_require "the table now has real headroom: count is far below max" \
  'c=$(cat /proc/sys/net/netfilter/nf_conntrack_count); m=$(cat /proc/sys/net/netfilter/nf_conntrack_max);
   [ "$m" -gt 0 ] && [ $((c * 4)) -lt "$m" ]'
answer_check "${ANSWER:-}"
verdict
