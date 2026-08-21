# The cluster's own PKI

Twice now you have run `etcdctl` by handing it three files out of `/etc/kubernetes/pki/etcd/`, and both times it worked without anyone asking who you were. That should bother you. You did not log in. There was no password, no prompt, nothing you had memorised. You presented files, and the store answered.

So: **what were those files, who made them, and what exactly did presenting them prove?**

### What does the cluster think your identity is?

Start with the credential you have been using all along without looking at it. `kubectl` has been talking to the API server since Act V, and its config is on your laptop:

```bash
kubectl config view --raw --minify -o jsonpath='{.users[0].user}' | head -c 120; echo
```

Two base64 blobs: `client-certificate-data` and `client-key-data`. Not a username. Decode the certificate and read what it says about you:

```bash
kubectl config view --raw --minify -o jsonpath='{.users[0].user.client-certificate-data}' \
  | base64 -d | openssl x509 -noout -subject -issuer -dates
```

```
subject=O=kubeadm:cluster-admins, CN=kubernetes-admin
issuer=CN=kubernetes
notBefore=...  notAfter=...
```

That is the OpenSSL 3.x rendering. macOS ships LibreSSL as `/usr/bin/openssl`, which prints the same fields slash-separated — `subject= /O=kubeadm:cluster-admins/CN=kubernetes-admin` — so if yours looks like that, nothing is wrong; you have a different `openssl` first in `PATH`.

Three fields there do real work, and none of them is a password.

**`CN=kubernetes-admin` is your username.** Not a hint at it — the API server takes the Common Name of the certificate you present and uses it as the identity of the request. **`O=kubeadm:cluster-admins` is your group** — and something, somewhere, has decided that this particular group may do anything at all in this cluster. Unusually for this course, you can go and look at that decision right now, even though nothing has explained the object it is written in:

```bash
kubectl get clusterrolebinding kubeadm:cluster-admins \
  -o jsonpath='{.roleRef.kind}/{.roleRef.name} <- {.subjects[*].kind}:{.subjects[*].name}{"\n"}'
```

```
ClusterRole/cluster-admin <- Group:kubeadm:cluster-admins
```

An object, in the store, saying *this group gets those powers*. Which is worth seeing precisely because it answers less than it appears to: you now know **where** the decision lives, and nothing about how the API server evaluates it, what a `ClusterRole` can express, or why the group in your certificate is the thing being matched. Hold that as a question — *what else could that object have said?* — because a later act is about exactly it. For now the mechanical point is enough: the certificate carries a name and a group, and a separate system reads them and decides. And **`issuer=CN=kubernetes`** is the reason the API server believes the name and group in the first place.

That is the whole authentication story for this credential. You are `kubernetes-admin` because a certificate signed by an authority the API server trusts says so.

Act III handed you TLS as a sealed box: a certificate is a signed statement, a chain of trust runs up to an authority, and you accepted a server's identity on that basis without opening the mathematics. This is the same box, pointed the other way — the *client* proving who it is to the server. What is inside the signature is still sealed, and stays sealed until a later act. What matters here is entirely mechanical: **a name, a group, an issuer, and an expiry date.**

> **Predict first —** that group binding grants full control of the cluster. Given that your identity is a file, and given that anyone who can read that file becomes you: what is the blast radius of `~/.kube/config` leaking? And how would you revoke it?

Nothing revokes it. There is no session to invalidate and no password to change, and the reason is visible in what the API server actually checks: a signature, and two dates. It consults no list of cancelled certificates. There is nowhere to write *this one is void* — so the credential is good until `notAfter`, and the only real remedies are drastic ones (re-issue the CA and invalidate everything) or slow ones (wait for expiry). That is the uncomfortable answer, and the reason certificate *lifetime* is an operational concern rather than a detail.

### Who signed it?

The issuer was `CN=kubernetes`. Go and find it on the control-plane node:

```bash
docker exec netlab-control-plane ls /etc/kubernetes/pki/
```

```
ca.crt  ca.key                       <- the cluster's root CA
apiserver.crt  apiserver.key         <- the API server's serving cert
apiserver-kubelet-client.crt/.key    <- API server proving itself TO kubelets
apiserver-etcd-client.crt/.key       <- API server proving itself TO etcd
front-proxy-ca.crt  front-proxy-ca.key  <- a third CA, for extension API servers
front-proxy-client.crt/.key          <- signed by that third CA, not by ca.crt
sa.pub  sa.key                       <- a key pair, not a CA. what signs it isn't a cert
etcd/                                <- a SEPARATE CA, for etcd only
```

Note `apiserver-etcd-client` in particular. In the first lesson of this act you read the store by presenting three files from `/etc/kubernetes/pki/etcd/`; that pair is the API server doing the same thing, with its own credential, signed by that separate etcd CA rather than by `ca.crt`. The two authorities meet in exactly one place, and it is a file you can list.

```bash
docker exec netlab-control-plane openssl x509 -noout -subject -dates \
  -in /etc/kubernetes/pki/ca.crt
```

`CN=kubernetes`, self-signed, with a ten-year lifetime. **`kubeadm`** generated it when the cluster was created — that is the standard cluster-bootstrapping tool, and it is what `kind` runs inside each node container to turn it into a Kubernetes node, which is why you have been seeing its name in your kind config all along. Every credential in the cluster descends from this file. Which is why the file next to it deserves a moment: **`ca.key` is the private key of that authority.** Anyone holding it can mint a certificate saying `CN=whoever, O=kubeadm:cluster-admins` — the group you read out of your own certificate two minutes ago — and become a cluster administrator, with nothing to revoke it afterwards.

There is a second group worth knowing about, because it is the one you will find in every article written before 2024 and it is not in your certificate:

```bash
docker exec netlab-control-plane grep client-certificate-data /etc/kubernetes/super-admin.conf \
  | awk '{print $2}' | base64 -d | openssl x509 -noout -subject
```

```
subject=O=system:masters, CN=kubernetes-super-admin
```

`system:masters` is special in a way `kubeadm:cluster-admins` is not: it is wired into the API server itself rather than into an object in the store, so it is not merely *bound* to full access — it **bypasses the permission check entirely**, which means it works even if the objects that grant permissions are broken or deleted. That is why `kubeadm` moved your everyday `admin.conf` off it and parked it in a second file: the break-glass credential is deliberately not the one you use daily. If you have read that `admin.conf` carries `O=system:masters`, that was true, and stopped being true.

Check the permissions and note the pattern:

```bash
docker exec netlab-control-plane stat -c '%a %U:%G %n' \
  /etc/kubernetes/pki/ca.key /etc/kubernetes/pki/ca.crt /etc/kubernetes/admin.conf
```

Certificates are world-readable; **keys are `600`, root-owned.** (`admin.conf` is `600` too, and is neither — it is protected because it *embeds* a key, which is the whole reason your `~/.kube/config` is as dangerous as the `Predict first` above concluded.) That distinction is the only thing standing between a shell on this node and permanent ownership of the cluster — which is also why `/etc/kubernetes/pki/etcd/` is a *separate* CA. A component trusted to talk to the API server is not thereby trusted to read the store directly.

### What about the components — did they get certificates too?

All of them, and they follow the same rule: the identity is in the `CN`.

```bash
for c in apiserver-kubelet-client front-proxy-client etcd/server; do
  docker exec netlab-control-plane openssl x509 -noout -subject -ext subjectAltName \
    -in /etc/kubernetes/pki/$c.crt 2>/dev/null | head -3
  echo "---"
done
```

The kubelet client certificate is just `CN=kube-apiserver-kubelet-client`, with no `O` at all — that is the API server proving itself *to* kubelets when it fetches logs or execs into a container, and it is a name without a group because on the other side of that connection it is an ordinary client being identified, not an administrator. Only one of the three prints a `subjectAltName`, and it is the one whose job is to be *dialled*: a client verifying a server checks the name it asked for against that list, so a purely outbound credential has no names to list. It is the same `subjectAltName` you wrote by hand with `-addext` when you made the Ingress certificate in [Act V](../act-5-kubernetes/06-ingress.md).

And the kubelets themselves get certificates the interesting way — they *ask*. A **`CertificateSigningRequest`** is an ordinary API object, a kind like any other: a kubelet generates a key, writes a CSR to the API server, and something approves it and writes back a signed certificate.

Which makes certificate issuance **the last lesson's reconciliation loop, doing PKI**. There is a controller watching for unsigned CSRs, and signing one is just another discrepancy it closes. It is also the mechanism by which a human gets a credential without anyone copying `ca.key` around: submit a CSR, have it approved, receive a certificate.

```bash
kubectl get csr
docker exec netlab-control-plane ls /var/lib/kubelet/pki/
```

On a cluster you built earlier today you will see the real rows, `Approved,Issued`, one per node, with a `REQUESTOR` of `system:node:<node>` or `system:bootstrap:<token>`. If instead you get `No resources found`, nothing is wrong — approved requests are garbage-collected after about an hour, so on an older cluster the requests are gone. The **result** is not: `/var/lib/kubelet/pki/` holds the certificate that arrived, which is the surviving evidence that the exchange happened.

Read that certificate, because it closes the loop on the rule this lesson opened with:

```bash
docker exec netlab-control-plane openssl x509 -noout -subject \
  -in /var/lib/kubelet/pki/kubelet-client-current.pem
```

```
subject=O=system:nodes, CN=system:node:netlab-control-plane
```

A username and a group again — but this time you are looking at the *output* of the exchange rather than at something `kubeadm` wrote at install time. The kubelet asked to be called `system:node:netlab-control-plane`, a controller agreed, and the answer is a file on disk. And notice one more thing, which is the evidence that no key was ever copied around: `kubelet.conf` does not embed a certificate the way `admin.conf` does — it points at this file by path. The credential arrived after the config was written.

### What happens when they expire?

> **Predict first —** you have now printed `-dates` twice: once for your own client certificate, once for `ca.crt`. Were those lifetimes the same? Before running the command below, say which certificates in this cluster you would expect to be the short-lived ones, and why a CA would be different.

```bash
docker exec netlab-control-plane kubeadm certs check-expiration
```

Two tables, and the shape of them is the answer: a long list of component certificates at **`364d`**, then a short list of the three certificate authorities at **`9y`**. Component certificates get one year; only the authorities get ten. (`9y`, not `10y` — the lifetime is ten years and the residual rounds down. And three authorities, which is the `ca` / `etcd-ca` / `front-proxy-ca` split you listed as files a moment ago, now shown as the thing each certificate was signed *by*.)

Which means every kubeadm cluster has a date on which it stops working, and the failure is memorable: `kubectl` returns a TLS error, the components cannot talk to each other, and the tool you would normally use to investigate is the one that has stopped.

(`super-admin.conf` is in that table too, so you meet it here whether or not you went looking for it above. And on a healthy cluster the command opens by saying it read configuration from the API server, possibly suggesting you re-upload a config file — that is chatter, not a warning.)

This command is the whole preventive story, and it makes a claim you should not take on trust: it needs no healthy cluster, because it only reads files. Test it by removing the cluster.

```bash
docker exec netlab-control-plane sh -c 'mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/'
sleep 15
kubectl get nodes                                                  # Unable to connect to the server
docker exec netlab-control-plane kubeadm certs check-expiration    # the full table, exit 0
docker exec netlab-control-plane sh -c 'mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/'
until kubectl get nodes 2>/dev/null; do sleep 2; done               # back in ~25s
```

That last line waits rather than guessing, because the API server takes a little over twenty seconds to start answering authenticated requests and a fixed `sleep` either wastes your time or lies to you. It is the same reason `kubeadm` is worth trusting here and a stopwatch is not.

`kubectl` is dead and the certificate audit still works. That asymmetry is not a curiosity — it is the reason this act insists on tools that read files, and it is exactly the situation you are in when the certificates have actually expired.

Renewal is deliberately not run here, because it rewrites live credentials:

```
kubeadm certs renew all           # renews everything kubeadm manages
kubeadm certs renew apiserver     # or one at a time
```

There is a catch worth knowing before you ever need it, and it follows from the last lesson rather than from anything about certificates. Renewal writes new files into `/etc/kubernetes/pki/`, but the API server, controller manager and scheduler read their certificates **at startup**. New files change nothing until the processes restart — and those processes are static Pods, so you restart them the way the last lesson established: by touching their manifests, not through `kubectl`.

Two more things renewal does not do. It does not touch `ca.crt`, because a new CA would invalidate every credential in the cluster at once. And it does not update your `~/.kube/config`, which holds a *copy* of a certificate — that comes from `/etc/kubernetes/admin.conf` on the control-plane node, and after renewal you copy it again.

> **Check yourself —** A cluster that worked yesterday now answers every `kubectl` command with a TLS error mentioning an expired certificate. You cannot use `kubectl` at all. Which of the things you have learned still work, and in what order would you use them?

<details>
<summary>Answer</summary>

Everything that reads files still works, and that is the entire toolkit here.

`kubeadm certs check-expiration` on the control-plane node needs no API server — it reads `/etc/kubernetes/pki/` off the disk and will name exactly which certificates lapsed. `kubeadm certs renew all` then rewrites them, also without needing a cluster.

Then the last lesson's mechanism does the rest: the control-plane components are static Pods holding their old certificates in memory, so they must restart to pick up the new files — move the four manifests out of `/etc/kubernetes/manifests/` and back, or restart the kubelet, and the kubelet starts them again from the files.

Finally your own credential: `admin.conf` embeds a certificate that was also renewed, so copy it to `~/.kube/config` again. Only at that point does `kubectl` start answering — and notice the ordering constraint underneath all of it. Every step had to be something that works with no API server, which is precisely why this act insists you can operate below `kubectl`.

</details>

<!-- figure -->

```
   /etc/kubernetes/pki/
     ca.crt / ca.key  ......... CN=kubernetes, self-signed, 10 years
        |    signs                  ca.key = permanent cluster ownership, 600 root
        +--> apiserver.crt ................. serving cert (has subjectAltName)
        +--> apiserver-kubelet-client.crt .. API server -> kubelet (CN only, no group)
        +--> admin.conf's client cert ...... CN=kubernetes-admin, O=kubeadm:cluster-admins
        |                                      CN = your username
        |                                      O  = your group
        +--> super-admin.conf's cert ....... O=system:masters -- break-glass; skips the
        |                                      permission check entirely
        +--> kubelet certs ................. requested via CSR objects (a control loop)
                                               O=system:nodes, CN=system:node:<node>

     etcd/ca.crt ................. a SEPARATE authority. API-server trust != store access
        +--> apiserver-etcd-client.crt ..... where the two authorities meet
     front-proxy-ca.crt .......... a THIRD authority, for extension API servers

   component certs: 1 YEAR (364d)      the three CAs: 10 years (shown as 9y)
   check:  kubeadm certs check-expiration     (reads files, needs no cluster)
   renew:  kubeadm certs renew all            (then RESTART the static Pods, and re-copy admin.conf)
```

> **You understand this when you can** say where the API server gets the username and group for a request that carried no password, name the field each comes from, and say why the cluster ships two administrator credentials rather than one; explain why `ca.key` is the most dangerous file on a control-plane node and why nothing can revoke a certificate minted with it; and describe, for a cluster whose certificates have expired, why `kubeadm certs renew all` alone does not fix it and what two further steps do.

**Which raises:** the certificates protect the door. But you have also seen that the thing behind the door is a few hundred keys in one directory on one node's disk, mounted into a static Pod by a `hostPath`. A credential that expires is an outage you recover from. What is the recovery when the *store itself* is gone?

---

← Prev: **[The reconciliation loop](03-the-reconciliation-loop.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Losing the cluster, and getting it back](05-etcd-backup-and-restore.md)** →
