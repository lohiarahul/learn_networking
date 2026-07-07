# netlab — the course lab image.
#
# nicolaka/netshoot gives you every networking tool (ss, tcpdump, dig, nc, ...)
# but no C compiler. The course also needs to build and run small C programs,
# so this image adds a compiler and bakes in the code/ directory. It also adds
# eza (a modern `ls`) so the course's "eza twin" commands run out of the box,
# and the *real* lsof (netshoot ships only a busybox stub that ignores -p/-i),
# which Act I's fd lessons rely on.
#
# Build (from the repo, on your Mac):
#   docker build -t netlab networking-fundamentals/code
#
# Run (Act I — one machine talking to itself, NO --network host):
#   docker run --rm -it --privileged --name lab netlab
#
# The sources land at /code; compile them inside the container with `cc`.
FROM nicolaka/netshoot

RUN apk add --no-cache build-base eza lsof

# netshoot's .zshrc does `cat motd` relative to $PWD; since WORKDIR is /code
# (not /root), that errors on every shell start. Point it at the real file.
RUN sed -i 's#^cat motd#cat /root/motd#' /root/.zshrc

COPY . /code
WORKDIR /code
RUN make            # pre-build minihttp + fd-demo (optional; you can rebuild anytime)
