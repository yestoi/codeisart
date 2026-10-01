#!/bin/sh
# The archive's run_clock.sh loop in POSIX sh: the clock prints its own next source, which is compiled
# and run every five seconds. The escape stands in for clear; the compile's warnings are discarded.
printf '\033[H\033[2J'
./prog | tee clock.c
sleep 5
while true; do
    cc -std=c11 -Wall -Wextra -pedantic -fsigned-char -O3 -o clock clock.c >/dev/null 2>&1 || exit 1
    printf '\033[H\033[2J'
    ./clock | tee clock.c
    sleep 5
done
