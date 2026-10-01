# The Pi is shared: every Pi command runs under the lock

The owner's rule (Q83 in decisions.md, 2026-10-01): the Pi 5 is shared with another session (promptviz's corpus
screen), and so is the Mac. While this file exists the rule holds; only the owner lifts it (he deletes this file).
`scripts/operator/reinject.py` prints this file after every compaction and at every session start;
`scripts/operator/guard_bash.py` refuses a Pi command that does not have this form.

- Every Pi command is one ssh call whose whole remote command runs under the lock, as one quoted string:
  `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -c '<script>'"`, or
  `ssh trey@codeisart.local 'flock -w 300 /tmp/pi5.lock <one command>'`. Nothing follows the closing quote.
- No scp, rsync or sftp to the Pi. What a command needs travels in the same call's standard input:
  `git -C /Users/trey/dev/codeisart archive --format=tar HEAD | ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -c '...'"`.
- Nothing is kept in the Pi's /tmp between calls. The scratch directory is a literal path under /tmp longer than
  12 characters with no `$` in it (`/tmp/it16-operator`): the call makes it, uses it and removes it.
- If the lock is not free in 300 seconds, `flock` exits 1 and prints nothing: do the Mac's work and try again
  later. A check that never got the lock is journaled as not run. Never run a Pi command without the lock, never
  touch `/tmp/pi5.lock` itself, never stop or signal a process on the Pi that the loop did not start.
- A script that ends with `exit 0` makes the ssh call exit 0 once the lock was taken: pass or fail is read
  from the printed output, not from the exit status.
- The Pi is the operator's inline tool only, never an agent's (config.md, Loop rule 9a, with what never runs there).
- The Mac is shared too: a suite time over the limit or a timing failure is measured once more before anything
  is decided on it, and the journal gives both readings.
- A Bash command whose text only quotes a Pi command (a commit message, a heredoc) is refused by the guard too:
  write such text with the Write or Edit tool, and name the Pi in a commit message without the ssh line.
