# Act IV drill 6 — "ctr works, crictl doesn't, and nobody touched crictl"
HINT='name the thing that was switched off, not the tool that failed.'
CAUSE_SHA='bc5a9b64b7b2584a0dff7387633f6ee3fd0f3c4b27f26d16ee38a70722d9199b
22058c3c2bd9be68f9838642bc8281b601d0e71ad3eedf8fcaab918d6fbd9833
a2da37712e481a551ff44d66414424d3753d05dfc5d0ea8b89ddcfad55de2eec
c52ca7b38eadc429896cacd542ea3dc44b6eddb09886cd9f7783221744a1da73
f33cb29d533ee21f1f7c863964652a804f7a0ad447dd6e6dfae46193e4b47a45'

lab_up
# The discriminator this drill is built on: containerd's own API (ctr) and the CRI service (crictl)
# are two different things riding the same socket, so the fix is proven by BOTH answering, not just one.
lab_require "containerd itself is up and ctr still talks to it" 'ctr version >/dev/null'
lab_require "and crictl now reaches the CRI service too" 'crictl version >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
