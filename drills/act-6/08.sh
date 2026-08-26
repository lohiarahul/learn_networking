# Act VI drill 8 — "the fix that worked last month is refused too"
HINT='name the kind of object whose cap the ReplicaSet hit, as kubectl spells it (singular).'
CAUSE_SHA='95c1086f32cd18c7b51d04ccf8fbdcc6b4aedae55babf874113bcdda9c53dbb4
b878a6801d9a9e68b30ed63430bb5e0bddcd984a37a3ee385abc27ff031c7fe7'

api_answers
nodes_ready 2
no_node_cordoned
absent "the drill's namespace is cleaned up" get namespace team-b
all_static_manifests
probe_scheduled
answer_check "${ANSWER:-}"
verdict
