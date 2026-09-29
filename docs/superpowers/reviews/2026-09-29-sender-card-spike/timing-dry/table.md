| run | scheduling | late | not ours | loop sd | loop worst | driver sd | driver worst | driver stamps | port sd | port worst | port stamps | queue max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sleep-other-qdisc | SCHED_OTHER priority 0, cpus 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 | 0 |  | 56 | 286 |  |  |  |  |  |  |  |
| sleep-fifo50-qdisc | failed: chrt: failed to set pid 0's policy: Operation not permitted |
| hybrid-other-qdisc | SCHED_OTHER priority 0, cpus 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 | 0 |  | 0 | 1 |  |  |  |  |  |  |  |
| hybrid-fifo50-qdisc | failed: chrt: failed to set pid 0's policy: Operation not permitted |
| spin-other-qdisc | SCHED_OTHER priority 0, cpus 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 | 0 |  | 15 | 253 |  |  |  |  |  |  |  |
| spin-fifo50-qdisc | failed: chrt: failed to set pid 0's policy: Operation not permitted |
| hybrid-other-qdisc-rows-sync | SCHED_OTHER priority 0, cpus 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 | 0 |  | 4 | 29 |  |  |  |  |  |  |  |
| hybrid-fifo50-qdisc-rows-sync | failed: chrt: failed to set pid 0's policy: Operation not permitted |
