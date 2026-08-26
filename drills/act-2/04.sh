# Act II drill 4 — "the name resolves to the wrong server, and DNS swears it's right"
HINT='name the file that answered before the resolver was ever asked.'
CAUSE_SHA='470f5d988d5e54a2ad3395160fe89f7100da54b019c53f4c91646b9d02226ae5
818891856c1e5b2f6e181ae8250f9fb62f92182b74b8a1ad0aa94d0f4fd06d21
4c82eb50a37db7a954b34dca424f5b1de92e8d9fd9dd3e3b205134c681857fd5'

lab_up
lab_require "no hosts-file override is left for example.com" \
  '! grep -Eq "^[^#]*[[:space:]]example\.com" /etc/hosts'
# The check the drill is actually about: the two answers agree again. `getent` walks nsswitch, `dig`
# talks to the resolver — and the whole bug was that only one of them ever consults that file.
# `getent hosts` and `dig +short A` are not comparable as strings, and finding that out is worth a
# comment: getent walks nsswitch and hands back whatever libc prefers — on a dual-stack host that is
# the **AAAA**, so it answers 2606:… while dig answers 104.20.…, and they disagree while both are
# right. The checkable claim is narrower and is the one the drill is about: the address libc now
# returns is one the resolver actually knows, rather than one a file made up.
lab_require "the address libc returns for example.com is one the resolver also knows" \
  'v4=$(getent ahostsv4 example.com | awk "{print \$1}" | sort -u);
   dns=$(dig +short example.com A);
   [ -n "$v4" ] && [ -n "$dns" ] || exit 1;
   for a in $v4; do printf "%s\n" "$dns" | grep -qx "$a" || exit 1; done'
answer_check "${ANSWER:-}"
verdict
