/* fd-demo.c — watch your own file-descriptor table grow, one open() at a time.
 *
 * A file descriptor is just a small integer the kernel hands back when you open
 * something. This program opens two things — a file and a socket — and then
 * waits, so you can go look at its table from another shell while it is alive.
 *
 * Build:  cc -Wall -o fd-demo fd-demo.c
 * Run:    ./fd-demo
 * Then, in a SECOND shell:
 *         ls -l /proc/$(pgrep -n fd-demo)/fd
 */
#include <stdio.h>
#include <fcntl.h>      /* open(), O_RDONLY */
#include <unistd.h>     /* getpid() — returns this process's ID */
#include <sys/socket.h> /* socket() */
#include <netinet/in.h> /* AF_INET, SOCK_STREAM */

int main(void) {
    /* getpid() returns the OS process ID — needed so we can tell the user
     * exactly which /proc/<pid>/fd directory to look at. */
    printf("my pid is %d\n\n", getpid());

    /* The kernel opens fds 0, 1, 2 for every new process automatically,
     * before main() runs.  They point at the terminal by default:
     *   0 = stdin  (read from keyboard)
     *   1 = stdout (write to screen)
     *   2 = stderr (write errors to screen)
     * That's why the next fd we get is always 3. */
    printf("fds 0, 1, 2 already exist (stdin, stdout, stderr)\n");

    /* open() asks the kernel to open a file and returns an integer handle.
     * O_RDONLY means open for reading only — we're not allowed to write.
     * The kernel always picks the lowest unused integer, so we get 3. */
    int file_fd = open("/etc/hostname", O_RDONLY);
    printf("open(\"/etc/hostname\") -> fd %d\n", file_fd);

    /* socket() also asks the kernel for a new fd — but this one represents
     * a network endpoint, not a file on disk.  From the kernel's perspective
     * it's the same thing: an integer in our fd table that we can read/write.
     * We get 4 because 3 is already taken by file_fd above. */
    int sock_fd = socket(AF_INET, SOCK_STREAM, 0);
    printf("socket(TCP)            -> fd %d   <-- a socket is just another fd\n", sock_fd);

    printf("\nLook at my table from another shell:\n");
    printf("    ls -l /proc/%d/fd\n", getpid());

    /* getchar() blocks waiting for the user to press Enter.
     * The process stays alive with its fds open so we can inspect them.
     * Once we return 0, main() exits, the kernel closes every fd, and they
     * disappear from /proc/<pid>/fd. */
    printf("\nPress Enter to exit (and watch the fds disappear)...\n");
    getchar();
    return 0;
}
