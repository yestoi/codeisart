# tour.sh: 1992/imc on the wall, six views of six seconds each (36 s, under the 40 s cap).
# This installation's adaptation of the archive's try.sh, without its build, key waits and pager;
# under the same licence (LICENSE.md). POSIX sh. stderr is dropped: imc writes a progress dot a row
# there, which shares the pty and would shift each row by one.

view() {
    printf '\033[H\033[2J'
    ./prog -text -size 78 22 "$@" 2>/dev/null
    sleep 6
}

view -mask 15 -limit 15
view -limit 256 -julia 0.5 -0.5
view -limit 1024 -julia 2 -2.5
view -limit 1024 -centre 1 2 -julia 2 -2.5
view -limit 256
view -limit 1024
exit 0
