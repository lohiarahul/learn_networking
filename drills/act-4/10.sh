# Act IV drill 10 — "nothing is wrong with DNS, and nothing resolves"
HINT='the policy is doing exactly what you told it to. Name the rule you never wrote.'
CAUSE_SHA='2095650208953cf86ea346b55357bc820415080d7e667b439611e4563153b005
38df310182102017d42fae5cfa82832d4b414e164427d0b4adc48892049f2051
3c138749060a88dfa7f61ffbf4ba5203647e65abfd91a4fab584d4f73ade7b4a
3c99d76897ac2f2a14cf005bde9e9dc8005e4e4a06aaceec3b79a6d7676e1b51
8791d2e0069ac71d2f62a61f288b5009b67bcbabcddd1224d0cff0dc57a1f5ef
93f8ad21c85f3c02f8846a0d735999247efa4e565d4e84fa5e253f44afe97215
a31afe0962e6a3a8c45e3efaa78083f6807b73b2cb31e21739ca3612a1134957
a61ac5d9127559c8dee0ac2267b4845ee2b21e792411150a5f6bb9a8ac04b31b
b627e6068b1e867ce0e2a0b1c80ccdab0f42b1c8eb2f037de2955948e8d4f7fc
c07164a0aace1dd825df9a1e43ba4258fbec16cf81a0716ea77b7a2960b52359
f8de45972c612d08705878420cb1189abfdbb5c5193ee52f42eb1a679de9a977
fd6134f0f2bb06396aa32518f909260291f8358217660167f06449c8a48ff90f'

lab_up
lab_require "the fw namespace is still there to test" 'ip netns list | grep -q "^fw"'
# Function, not configuration. The wrong fix — reopening the policy, or a blanket ACCEPT — makes every
# check below pass except this one, which is why it comes first: the door must still be shut by default.
lab_require "the INPUT policy is still DROP (you fixed the ruleset, not the posture)" \
  'ip netns exec fw iptables -S INPUT | grep -qx -- "-P INPUT DROP"'
lab_require "and no blanket accept was added in its place" \
  '! ip netns exec fw iptables -S INPUT | grep -qxE -- "-A INPUT -j ACCEPT"'
# Loopback: a process on this host can talk to another process on this host again. Act I's whole premise.
lab_require "loopback works again inside fw" \
  'ip netns exec fw curl -sf -o /dev/null --max-time 3 http://127.0.0.1:8080'
# The reply problem itself, proven without needing the internet: fw dials the far end of its own veth,
# where the lab is listening, and the answer has to survive INPUT to get back.
lab_require "and a reply to a connection fw opened now gets back in" \
  'ip netns exec fw curl -sf -o /dev/null --max-time 3 http://10.75.0.1:8090'
# And it is the flow table doing it, not a port range someone guessed at.
lab_require "the rule that admits it consults conntrack rather than naming ports" \
  'ip netns exec fw iptables -S INPUT | grep -E -- "--ctstate|--state" | grep -qE "ESTABLISHED"'
answer_check "${ANSWER:-}"
verdict
