/* hello: the sample entry. A band of # sweeps on a wave for about 3 seconds,
 * then the screen clears and it says hello. No input, no raw mode. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int env_int(const char *name, int dflt)
{
    const char *s = getenv(name);
    int v = s ? atoi(s) : 0;
    return v > 0 ? v : dflt;
}

int main(void)
{
    int rows = env_int("LINES", 23);
    int cols = env_int("COLUMNS", 80);
    int frames = 60;   /* 60 frames at 20 a second: about 3 seconds */
    int width = 6;
    int span = cols - width;
    int leftover = 0;  /* unused on purpose: the one -Wall warning */

    if (span < 1)
        span = 1;
    printf("\033[?25l\033[2J");
    for (int f = 0; f < frames; f++) {
        printf("\033[H");
        for (int r = 0; r < rows; r++) {
            /* triangle wave over the frames, shifted by the row: a ripple */
            int p = (f * 2 + r) % (2 * span);
            int col = p < span ? p : 2 * span - p;
            printf("%*s", col, "");
            for (int i = 0; i < width; i++)
                putchar('#');
            printf("\033[K");  /* erase the trail of earlier frames */
            if (r < rows - 1)  /* no newline on the last row: it would scroll */
                putchar('\n');
        }
        fflush(stdout);
        usleep(50000);
    }
    printf("\033[2J\033[H\033[?25h");
    printf("hello, world\n");
    return 0;
}
