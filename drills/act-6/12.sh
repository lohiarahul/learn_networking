# Act VI drill 12 — "we capped the kubelet's memory and the cap is not there"
#
# Verify by function, not by configuration. "The drop-in file exists" was already true when the drill
# was broken — that was the whole symptom. So the checks below assert the value reached the two places
# that can only agree once systemd has actually re-read the file: its own in-memory definition, and the
# byte in the cgroup. A learner who deleted the drop-in to make `MemoryMax=infinity` "correct" fails,
# because check 2 needs the number present.
HINT='name what systemd had not done, not what the file said.'
CAUSE_SHA='ee1cbe0e64b20c13cf48de1fb11cc024f1fee85b4f01dfaed2d1adbdc7cc1ec4
ebaa5becb8bb27d61371045688d4a42a85cd6afa58251cf0bdb925d324e98ed0
17a99c25b6bd0ef1b3ee4dbf43fd3773c226f4f8e9403aa62cdf3039b467aed2
e8206fbb69957ae92cdc3c4442a5ea302de4b636527d09499b6c33c249396f30
a5a1ce6e2e678d1ac129e878c09a3db49a36194d70c6f8e2d484317e74af15e8
72f0c5111543e7e6c07949b7aa695b5e3cf7c6b29090a475f8714713e5407ec2
3aebde683ea86d951224eaca24ab0f593efee45e2b8f0b421c87b62768d5b28e
016e128659183df91e65ad755e97ea422f2aed5e0524c5e4673801cd53a48e77'

require "the worker's kubelet is running again" \
  docker exec "$WORKER" systemctl is-active --quiet kubelet

# The drop-in has to be in the merged definition — this is the fact that was false, and the one
# `daemon-reload` changes. Reading DropInPaths rather than the directory is deliberate: the directory
# was already right.
require "systemd has actually loaded the drop-in (it is in DropInPaths, not merely on disk)" \
  sh -c 'docker exec '"$WORKER"' systemctl show kubelet -p DropInPaths | grep -q 20-memcap.conf'

require "and its value is in systemd's own definition of the unit" \
  sh -c 'docker exec '"$WORKER"' systemctl show kubelet -p MemoryMax | grep -q "MemoryMax=536870912"'

# Function: a unit setting is not honoured until it is a byte in a cgroup file. This is the check that
# cannot be satisfied by anything except a running process placed under the reloaded definition.
require "the cap is a real byte in the kubelet's cgroup, not just a systemd property" \
  sh -c 'docker exec '"$WORKER"' cat /sys/fs/cgroup/kubelet.slice/kubelet.service/memory.max | grep -qx 536870912'

# The node must still work. A cap applied by stopping the kubelet is not a fix.
require "the worker is still Ready — the cap did not cost you the node" \
  sh -c '[ "$(kubectl get node '"$WORKER"' --no-headers 2>/dev/null | awk "{print \$2}")" = "Ready" ]'

answer_check "${ANSWER:-}"
verdict
