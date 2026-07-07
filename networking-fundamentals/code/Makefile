# Builds the course's C programs. Run `make` inside the lab container
# (the netlab image has a compiler); on macOS you do NOT build these on the
# host — they're Linux programs, so they compile and run inside the container.

CFLAGS = -Wall -O2
BINS   = minihttp fd-demo

all: $(BINS)

%: %.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(BINS)

.PHONY: all clean
