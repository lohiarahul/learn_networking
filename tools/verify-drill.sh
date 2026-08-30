#!/usr/bin/env bash
# verify-drill.sh — check that a learner actually fixed a drill, and actually knows why.
#
#   tools/verify-drill.sh <act> <drill> "<your diagnosis>"
#   tools/verify-drill.sh act-6 1 "kube-scheduler"
#
# Exits 0 only if every state check passes *and* the diagnosis you typed matches the cause. The
# expected answer is stored as a hash, so reading `drills/` will not tell you what it is —
# see the argument in `drills/lib.sh`.
set -uo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)

usage() {
  cat >&2 <<USAGE
usage: tools/verify-drill.sh <act> <drill> "<your diagnosis>"
       tools/verify-drill.sh --list

  <act>    act-1 … act-11        <drill>  the drill number
  The third argument is your own one-line diagnosis. It is required: a drill you fixed
  without being able to name the cause is a drill you have not done.
USAGE
  exit 2
}

if [ "${1:-}" = "--list" ]; then
  for d in "$REPO"/drills/act-*/; do
    a=$(basename "$d"); n=$(ls "$d" 2>/dev/null | grep -c '^[0-9]*\.sh$')
    printf '%-8s %s verifier(s)\n' "$a" "$n"
  done
  exit 0
fi

[ $# -ge 2 ] || usage
ACT="$1"; N="$2"; ANSWER="${3:-}"
SCRIPT=$(printf '%s/drills/%s/%02d.sh' "$REPO" "$ACT" "$N" 2>/dev/null)

if [ ! -f "$SCRIPT" ]; then
  printf 'no verifier for %s drill %s (looked for %s)\n' "$ACT" "$N" "${SCRIPT#$REPO/}" >&2
  printf 'run tools/verify-drill.sh --list to see what is covered.\n' >&2
  exit 2
fi

printf '%s drill %s — verifying\n\n' "$ACT" "$N"
# shellcheck source=/dev/null
. "$REPO/drills/lib.sh"
# shellcheck source=/dev/null
. "$SCRIPT"
