/* minihttp.c — the smallest HTTP server worth keeping.
 *
 * This one program is the spine of the whole course. Every act does something
 * new to it: here in Act I you watch its file descriptors and its port; in
 * Act III you capture its handshake; in Act IV you run it inside a network
 * namespace; in Act V you containerize it. It is nothing but a few file
 * descriptors that it read()s and write()s — which is the entire point.
 *
 * Build:  cc -Wall -o minihttp minihttp.c
 * Run:    ./minihttp 8080
 * Test:   curl localhost:8080        (from another shell)
 */

/* Standard library headers — printf, exit, memset, read/write, socket calls */
#include <stdio.h>       /* printf */
#include <stdlib.h>      /* atoi (string → integer) */
#include <string.h>      /* strlen, snprintf */
#include <unistd.h>      /* read, write, close — same calls used for regular files */
#include <sys/socket.h>  /* socket, bind, listen, accept */
#include <netinet/in.h>  /* struct sockaddr_in, htons, htonl */

/* argc = number of command-line arguments, argv = the arguments as strings.
 * argv[0] is the program name, argv[1] onwards are what the user typed. */
int main(int argc, char **argv) {
    /* If the user typed a port number use it, otherwise default to 8080.
     * atoi converts the string "8080" to the integer 8080. */
    int port = (argc > 1) ? atoi(argv[1]) : 8080;

    /* socket() asks the kernel for a new file descriptor that can send/receive
     * network data.  AF_INET = IPv4, SOCK_STREAM = TCP (reliable, ordered).
     * The returned integer (listen_fd) works exactly like a file descriptor
     * from open() — you read() and write() bytes through it. */
    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);

    /* SO_REUSEADDR lets us restart the server immediately after killing it,
     * instead of waiting ~60 s for the OS to release the port. */
    int yes = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);

    /* sockaddr_in is a struct that holds the address we want to listen on.
     * {0} zero-initialises every field (equivalent to memset(&addr,0,…)). */
    struct sockaddr_in addr = {0};
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);   /* 0.0.0.0 — every interface */
    addr.sin_port        = htons(port);          /* htons converts to network byte order (big-endian) */

    /* bind() attaches the socket fd to the address+port we filled in above.
     * Without this, the kernel doesn't know which port to send traffic to. */
    bind(listen_fd, (struct sockaddr *)&addr, sizeof addr);

    /* listen() marks the socket as passive — it won't send data itself, it
     * just waits for incoming connections.  16 = max pending connections to
     * queue while we're busy handling the current one. */
    listen(listen_fd, 16);

    printf("minihttp: pid %d, listening on 0.0.0.0:%d via fd %d\n",
           getpid(), port, listen_fd);
    printf("look at me from another shell:  ls -l /proc/%d/fd\n", getpid());

    /* Loop forever — a real server never exits on its own. */
    for (;;) {
        /* accept() blocks (pauses) until a client connects.  When one does,
         * the kernel creates a BRAND NEW file descriptor just for that
         * connection and returns it.  listen_fd keeps waiting for the next one.
         * This is how one server talks to many clients: each gets its own fd. */
        int conn_fd = accept(listen_fd, NULL, NULL);

        /* Read the HTTP request the client sent.  It's just bytes in a buffer —
         * the same read() call used for files and stdin. */
        char buf[1024];
        ssize_t n = read(conn_fd, buf, sizeof buf - 1);
        if (n > 0) buf[n] = '\0';   /* null-terminate so printf treats it as a string */
        printf("\n--- a request arrived on fd %d ---\n%s\n", conn_fd, buf);

        /* Build a minimal HTTP response.  \r\n is the line ending HTTP requires.
         * The blank line (\r\n after the last header) separates headers from body. */
        const char *body = "hello from a file descriptor\n";
        char resp[256];
        int len = snprintf(resp, sizeof resp,
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: %zu\r\n"
            "Connection: close\r\n"
            "\r\n%s", strlen(body), body);

        /* write() sends our response bytes into the connection fd — same call
         * used to write to a file or to stdout (fd 1). */
        write(conn_fd, resp, len);

        /* close() releases this connection's fd.  The client sees the connection
         * drop, which signals that the response is complete. */
        close(conn_fd);
    }
}
