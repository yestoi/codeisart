"""tools/sender_spike/timing_matrix.py: the runs of the brief's step 6 and the table made of them."""
from tools.sender_spike import send, timing_matrix as tm

OUTPUT = """send: 60 fps for 10 s, then 0.2 s black; order sync-rows; sync x2, 112 bytes; wait hybrid (spin 2 ms), stamps
send: on enp5s0; scheduling: SCHED_FIFO priority 50, cpus 0,1
send: sent 600 frames and 12 black; 2 late
send: measured 60.000 fps over the picture
send: sync to sync, ms: mean 16.667 sd 0.004 min 16.650 max 16.690 p50 16.667 p99 16.680
send: sync to sync less the period of 16.667 ms, us: count
    -20 to 20           599
send: added to each sync, us: mean 0.0 sd 0.0 min 0.0 max 0.0
send: sync after its tick, less the added time, us: mean 0.3 sd 1.0 min 0.2 max 17.0 p50 0.2 p99 0.9
send: burst, first packet to last, us: mean 310.2 sd 12.0 min 290.1 max 450.9
send: the port sent 40805 packets during the run: 40800 ours, 5 not ours
send: driver: 600 of 600 stamps
send: sync to sync at the driver, ms: mean 16.667 sd 0.012 min 16.600 max 16.800 p50 16.667 p99 16.700
send: port: 598 of 600 stamps
send: sync to sync at the port, ms: mean 16.667 sd 0.013 min 16.590 max 16.810 p50 16.667 p99 16.701
send: from the queue to the driver, us: mean 4.1 sd 2.0 min 2.0 max 31.5 p50 3.9 p99 9.0
send: the sync behind the last row at the driver, us: mean 7.9 sd 3.0 min -20.0 max 12.0 p50 8.0 p99 11.0
send: the sync left before the last row of its frame in 3 of 600 frames
send: the port's queue held packets during the run: 7 requeues, 14 new flows; packets may have left in another order than they were sent
"""


def test_the_matrix_is_every_wait_with_every_scheduling_and_queue():
    runs = tm.commands("enp5s0", "/v/bin/python", "/out", 10)
    names = [name for name, argv in runs]
    assert len(names) == len(set(names)) == 18
    # the old test sender's way, in its own order: where the queue was seen to let the sync overtake
    assert "sleep-other-qdisc-rows-sync" in names and "sleep-other-bypass-rows-sync" in names
    assert names[0] == "hybrid-fifo50-bypass-stamp-sw"     # the wall's own form of the command, first
    assert "hybrid-fifo50-bypass-rows-sync" in names       # the base's order past the queue: no overtaking
    for wait in ("sleep", "hybrid", "spin"):
        for sched in ("other", "fifo50"):
            for queue in ("qdisc", "bypass"):
                assert "%s-%s-%s" % (wait, sched, queue) in names
    assert "hybrid-fifo50-qdisc-rows-sync" in names and "hybrid-other-qdisc-rows-sync" in names


def test_a_run_of_the_matrix_is_a_send_command_that_the_safety_rules_allow():
    for name, argv in tm.commands("enp5s0", "/v/bin/python", "/out", 10):
        at = argv.index("/v/bin/python")
        assert argv[:at] in ([], ["chrt", "-f", "50"])
        assert argv[at + 1].endswith("tools/sender_spike/send.py")
        plan = send.plan_from(argv[at + 2:])
        assert plan.stamp == ("sw" if name.endswith("stamp-sw") else "hw")
        assert plan.iface == "enp5s0" and plan.seconds == 10 and plan.pixel == 25
        assert plan.sync == send.SyncSpec() and plan.bright_reps == 2 and plan.sync_reps == 2   # base packets
        assert plan.log == "/out/%s.csv" % name
        assert (argv[:at] != []) == ("fifo50" in name)
        assert plan.qdisc_bypass == ("bypass" in name)
        assert plan.wait == name.split("-")[0]
        assert plan.order == ("sync-rows" if name.count("-") == 2 else "rows-sync")
        assert ("other" in name) == (argv[:at] == [])


def test_a_runs_output_is_read_into_numbers():
    got = tm.parse(OUTPUT)
    assert got["scheduling"] == "SCHED_FIFO priority 50, cpus 0,1"
    assert got["late"] == 2 and got["not ours"] == 5
    assert got["loop"] == {"mean": 16.667, "sd": 0.004, "min": 16.650, "max": 16.690, "p50": 16.667, "p99": 16.680}
    assert got["driver"]["sd"] == 0.012 and got["port"]["max"] == 16.810
    assert got["stamps"] == {"driver": (600, 600), "port": (598, 600)}
    assert got["queue"]["max"] == 31.5
    assert got["overtaken"] == (3, 600) and got["queue events"] == (7, 14)


def test_output_without_stamps_has_no_driver_numbers():
    got = tm.parse(OUTPUT.split("send: driver")[0])
    assert "driver" not in got and "port" not in got and got["loop"]["sd"] == 0.004


def test_the_table_has_a_row_a_run_in_microseconds():
    text = tm.table([("hybrid-fifo50-qdisc", tm.parse(OUTPUT), ""), ("spin-other-bypass", None, "OSError: [Errno 105]")],
                    fps=60)
    lines = text.splitlines()
    assert lines[0].startswith("| run | scheduling | late | not ours | loop sd | loop worst |")
    assert lines[0].rstrip(" |").endswith("| queue max | order broken | queue held")
    row = [c.strip() for c in lines[2].split("|")]
    assert row[1] == "hybrid-fifo50-qdisc" and row[2] == "SCHED_FIFO priority 50, cpus 0,1"
    assert row[3:5] == ["2", "5"]
    assert row[5:7] == ["4", "23"]                          # sd 0.004 ms; worst: 16.690 - 16.667 = 23 us
    assert row[7:10] == ["12", "133", "600/600"]            # driver sd, worst, stamps
    assert row[10:13] == ["13", "143", "598/600"]           # port
    assert row[13] == "31.5"                                # the longest time in the queue
    assert row[14:16] == ["3/600", "7, 14"]
    assert "OSError: [Errno 105]" in lines[3] and "spin-other-bypass" in lines[3]


def test_a_dry_matrix_opens_no_socket():
    runs = tm.commands("enp5s0", "/v/bin/python", "/out", 5, dry_run=True)
    assert len(runs) == 9                                   # the queue does not matter without a socket
    for name, argv in runs:
        at = argv.index("/v/bin/python")
        plan = send.plan_from(argv[at + 2:])
        assert plan.dry_run and plan.stamp == "" and not plan.qdisc_bypass and plan.seconds == 5


def test_the_matrix_needs_the_owners_word_that_the_card_is_not_on_the_cable(capsys):
    import pytest
    ran = []
    with pytest.raises(SystemExit) as e:
        tm.main(["--out", "/tmp/never"], runner=lambda *a, **k: ran.append(a))
    assert e.value.code == 2 and ran == []
    assert "--card-unplugged" in capsys.readouterr().err


def test_the_dry_matrix_needs_no_word(tmp_path):
    ran = []

    class Done:
        returncode, stdout, stderr = 0, OUTPUT, ""

    assert tm.main(["--dry-run", "--out", str(tmp_path)], runner=lambda cmd, **k: ran.append(cmd) or Done()) == 0
    assert len(ran) == 9


def test_with_the_owners_word_the_matrix_runs(tmp_path):
    ran = []

    class Done:
        returncode, stdout, stderr = 0, OUTPUT, ""

    assert tm.main(["--card-unplugged", "--out", str(tmp_path)],
                   runner=lambda cmd, **k: ran.append(cmd) or Done()) == 0
    assert len(ran) == 18
    assert "order broken" in (tmp_path / "table.md").read_text()
