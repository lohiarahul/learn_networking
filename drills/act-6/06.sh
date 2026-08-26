# Act VI drill 6 — "the drain has been running for half an hour"
HINT='name the kind of object that refused the eviction, as kubectl spells it (singular, or its
three-letter short name).'
CAUSE_SHA='918b20bb00c42f8884a17e7b134f25c77a0930c859c9382bde88acf8f4dd866b
e4bab4de957bbc2be2e44ad645ff0520cdbdce7808cec3bb8b88c4b4e4dc04ba'

api_answers
nodes_ready 2
no_node_cordoned
absent "the drill's Deployment is cleaned up" get deployment checkout
absent "the drill's PodDisruptionBudget is cleaned up" get pdb checkout-pdb
# A drain that "finished" because the budget was deleted is not the same as understanding it. The
# functional check is that the worker takes work again.
probe_scheduled
answer_check "${ANSWER:-}"
verdict
