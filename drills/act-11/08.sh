# Act XI drill 8 — a ratio that is provably wrong, from a rule everyone reviewed
HINT='name which operation has to happen first, sum or divide, and say why averaging three
per-replica ratios lets a low-traffic replica outvote the one carrying most of the traffic.'
CAUSE_SHA='756b2c04b837c7ac8539fc387e60cebc21f52788c9cca5b1a491e8c27610ac58
d173c885d56833b1de40c244ff88d30dccc9d28fbf848b6e36c564851313a66e
72529b92ffa73fae7b2154bf0cf70745addc394f749457cd3f84d65346beb656
d14184835816ccb38fecfbecb6f74674fcff4ffd373d62577c858fd92660ee35'

# A paper drill: recompute both the reviewed rule's arithmetic and the corrected rule's, on the
# drill's own numbers, and on a re-weighted traffic split — proving the two formulas are not the
# same thing rather than asserting it.
compute() {
  # args: e1 r1 e2 r2 e3 r3
  python3 - "$@" <<'PY'
import sys
e1,r1,e2,r2,e3,r3 = map(float, sys.argv[1:7])
avg_of_ratios = ((e1/r1) + (e2/r2) + (e3/r3)) / 3
ratio_of_sums = (e1+e2+e3) / (r1+r2+r3)
print(f"{avg_of_ratios:.6f} {ratio_of_sums:.6f}")
PY
}

drills_own_numbers_diverge() {
  local out a s
  out=$(compute 1 10 1 10 1 990)
  a=$(printf '%s' "$out" | awk '{print $1}')
  s=$(printf '%s' "$out" | awk '{print $2}')
  require_eq "sum(errors)/sum(requests) on the drill's own numbers is 0.002970" "0.002970" printf '%s' "$s"
  if python3 -c "exit(0 if $a/$s > 10 else 1)" 2>/dev/null; then
    ok "avg-of-per-replica-ratios ($a) overstates the true fleet rate ($s) by more than 10x"
  else
    bad "avg-of-per-replica-ratios overstates the true fleet rate by more than 10x" "avg=$a sum-ratio=$s"; return 1
  fi
}

heavier_skew_widens_the_gap() {
  local out1 out2 gap1 gap2 a1 s1 a2 s2
  out1=$(compute 1 10 1 10 1 990)
  a1=$(printf '%s' "$out1" | awk '{print $1}'); s1=$(printf '%s' "$out1" | awk '{print $2}')
  out2=$(compute 1 10 1 10 1 99000)
  a2=$(printf '%s' "$out2" | awk '{print $1}'); s2=$(printf '%s' "$out2" | awk '{print $2}')
  gap1=$(python3 -c "print($a1/$s1)")
  gap2=$(python3 -c "print($a2/$s2)")
  if python3 -c "exit(0 if $gap2 > $gap1 else 1)" 2>/dev/null; then
    ok "skewing traffic further toward the low-error replica widens the gap (${gap1}x -> ${gap2}x)"
  else
    bad "skewing traffic further widens the gap" "gap did not grow: ${gap1}x -> ${gap2}x"; return 1
  fi
}

drills_own_numbers_diverge && heavier_skew_widens_the_gap
answer_check "${ANSWER:-}"
verdict
