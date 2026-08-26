# Act I drill 1 — "it works for me, but they can't reach it"
HINT='name the address the server bound to, or the field in `ss` that showed it.'
CAUSE_SHA='64edaa3fb9310e98cdb183cddbf156d9964a05c017fa7f8ee3c262909fa36759
053abfc48963f2cb94ebde98f96d10979cda070733331e3e9cf408f0df2d8cc9
ce06b5fcb8ec08cad175ef03297008eeac3db95fc02f633ed00ad6aa26c6cfe6
4592e84ddb4f8a479660331e58d54a6c2a3590084551148e1fdd53145219cfae
2ac45a84db86ac6331d6a7f0892414ff175d12c8dc1a6c4601f6e164864d23fc'

# Run this before the drill's `kill %1`, with the fixed server still listening.
lab_up
# Function, not configuration: knock on the *outside* door. That is the door kube-proxy knocks on, and
# the whole reason this drill is the first one in the course.
lab_require "the server answers on the container's own address, not only on loopback" \
  'curl -sf -o /dev/null --max-time 3 "$(hostname -i | awk "{print \$1}"):8080"'
lab_require "and ss agrees — the listening socket is on 0.0.0.0, not 127.0.0.1" \
  'ss -tln | awk "\$4 ~ /:8080\$/ {print \$4}" | grep -Eq "^(0\.0\.0\.0|\*):8080$"'
answer_check "${ANSWER:-}"
verdict
