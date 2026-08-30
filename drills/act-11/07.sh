# Act XI drill 7 — the latency report and the SLO disagree
HINT='name the relationship between the SLO threshold and the histogram bucket edges, not the
percentile formula.'
CAUSE_SHA='baae5a1e60c3e77a2b89bd0c94b1c5263f431b7f1675e1f6d7dacdbf9f4ff68f
4e4f8d484d903ad08a7bc31786a108187e4c7f0e1defc62583437180c32c9418
a82f505039cadb4b04059cbb62c3677ce7005cd8547212e4d0cfabd84e62b820
7a0d2e82a4ebbd8f6b0cadfeebb15d2de8036adb4e27320897ad409ce67a2f3a'

# A paper drill: there is no cluster state to check, so this recomputes the interpolation the
# answer describes and checks it against the drill's own numbers, the way Act X's paper drills
# compute the counterexample rather than inventing an assertion.
interpolation_matches() {
  local p99; p99=$(python3 -c "
rank = 0.99 * 54
lo, hi = 0.05, 0.1
c_lo, c_hi = 53, 54
frac = (rank - c_lo) / (c_hi - c_lo)
print(round(lo + frac * (hi - lo), 3))
")
  if [ "$p99" = "0.073" ]; then ok "the interpolated p99 recomputes to ${p99}s, as the answer states"
  else bad "the interpolated p99 recomputes to 0.073s" "got $p99 — check the drill's own bucket numbers"; return 1; fi
  # 0.06 (the SLO) sits strictly between 0.05 and 0.1: no bucket edge equals it.
  if python3 -c "exit(0 if 0.05 < 0.06 < 0.1 else 1)"; then
    ok "0.06 is not a bucket edge — it sits strictly inside (0.05, 0.1]"
  else
    bad "0.06 is not a bucket edge" "the SLO boundary would need to be a genuine edge for this drill to hold"; return 1
  fi
}

interpolation_matches
answer_check "${ANSWER:-}"
verdict
