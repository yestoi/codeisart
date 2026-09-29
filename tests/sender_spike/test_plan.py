"""The flags of tools/sender_spike/send.py: one flag, one variable; and the brief's safety rules."""
import dataclasses

import pytest

from tools.sender_spike import send


def flat(plan):
    d = dataclasses.asdict(plan)
    sync = d.pop("sync")
    d.update({"sync." + k: v for k, v in sync.items()})
    return d


def differs(plan, base=None):
    base = flat(base or send.plan_from([]))
    return {k: v for k, v in flat(plan).items() if base[k] != v}


def test_no_flags_is_the_test_sender_at_60():
    plan = send.plan_from([])
    assert plan.sync == send.SyncSpec()
    assert (plan.sync_reps, plan.bright_reps, plan.bright_level) == (2, 2, 25)
    assert (plan.row_tail, plan.order, plan.gap_ms) == (b"\x08\x88", "rows-sync", 0.0)
    assert (plan.fps, plan.seconds, plan.tail_seconds) == (60.0, 10.0, 1.0)
    assert (plan.pixel, plan.picture, plan.jitter_ms) == (128, "bars", 0.0)
    assert (plan.wait, plan.spin_ms, plan.qdisc_bypass, plan.dry_run) == ("hybrid", 2.0, False, False)


@pytest.mark.parametrize("argv, change", [
    (["--fps", "60.32"], {"fps": 60.32}),
    (["--fps", "30"], {"fps": 30.0}),
    (["--sync-reps", "1"], {"sync_reps": 1}),
    (["--bright-reps", "1"], {"bright_reps": 1}),
    (["--gap-ms", "12"], {"gap_ms": 12.0}),
    (["--order", "sync-rows"], {"order": "sync-rows"}),
    (["--jitter-ms", "0.25"], {"jitter_ms": 0.25}),
    (["--picture", "scroll"], {"picture": "scroll"}),
    (["--pixel", "25"], {"pixel": 25}),
    (["--wait", "spin"], {"wait": "spin"}),
    (["--wait", "sleep"], {"wait": "sleep"}),
    (["--qdisc-bypass"], {"qdisc_bypass": True}),
    (["--seconds", "5"], {"seconds": 5.0}),
    (["--tail-seconds", "0"], {"tail_seconds": 0.0}),
    (["--brightness", "0.2"], {"bright_level": 51, "sync.level": 51}),
    (["--bright-level", "0.2"], {"bright_level": 51}),
    (["--sync-level", "0.2"], {"sync.level": 51}),
    (["--sync-level", "0.4"], {"sync.level": 102}),
])
def test_a_flag_changes_one_variable(argv, change):
    assert differs(send.plan_from(argv)) == change


# A flag that changes what a packet holds, or takes the brightness packet away, leaves the card's
# brightness in doubt: nobody knows what the fields mean. It dims the picture as well (safety rule 3).
@pytest.mark.parametrize("argv, change", [
    (["--source-type", "00"], {"sync.source_type": 0}),
    (["--byte36", "00"], {"sync.byte36": 0}),
    (["--bright-reps", "0"], {"bright_reps": 0}),
    (["--sync-len", "1036"], {"sync.length": 1036}),
    (["--row-tail", "0000"], {"row_tail": b"\x00\x00"}),
    (["--counter", "on"], {"sync.counter": True}),
    (["--bytes16", "ffffff"], {"sync.bytes16": b"\xff\xff\xff"}),
    (["--byte26", "01"], {"sync.byte26": 1}),
    (["--declared-rate", "013c"], {"sync.declared_rate": b"\x01\x3c"}),
    (["--declared-rate", "011e"], {"sync.declared_rate": b"\x01\x1e"}),
])
def test_a_flag_that_touches_brightness_changes_one_variable_against_the_dim_base(argv, change):
    plan = send.plan_from(argv)
    assert plan.pixel == 25
    assert differs(plan, send.plan_from(["--pixel", "25"])) == change


def test_s2_header_is_the_s2s_header_in_the_base_layout():
    plan = send.plan_from(["--s2-header"])
    assert plan.sync == send.S2_HEADER
    sync_fields = {k for k in differs(plan, send.plan_from(["--pixel", "25"]))}
    assert all(k.startswith("sync.") for k in sync_fields)
    assert "sync.length" not in sync_fields


def test_s2_is_the_whole_imitation():
    plan = send.plan_from(["--s2"])
    assert plan.sync == send.S2_SYNC
    assert (plan.sync_reps, plan.bright_reps, plan.row_tail, plan.order) == (1, 0, b"\x00\x00", "sync-rows")
    assert plan.pixel == 25
    assert plan.fps == 60.0                                   # the rate stays a flag of its own


def test_a_flag_overrides_its_field_of_a_preset():
    plan = send.plan_from(["--s2", "--sync-reps", "2", "--byte36", "05", "--counter", "off"])
    assert plan.sync_reps == 2 and plan.sync.byte36 == 5 and plan.sync.counter is False
    assert differs(plan, send.plan_from(["--s2"])) == {
        "sync_reps": 2, "sync.byte36": 5, "sync.counter": False}


def test_h3_declares_30():
    plan = send.plan_from(["--s2", "--declared-rate", "011e", "--fps", "30"])
    assert plan.sync.declared_rate == b"\x01\x1e" and plan.fps == 30.0


# --- safety rules

@pytest.mark.parametrize("argv, words", [
    (["--brightness", "0.5"], "0.4"),
    (["--bright-level", "0.41"], "0.4"),
    (["--source-type", "00", "--pixel", "128"], "25"),
    (["--s2", "--pixel", "26"], "25"),
    (["--bright-reps", "0", "--pixel", "128"], "25"),
    (["--sync-level", "1.0"], "source type 00"),                          # 0xff is the S2's own, no one else's
    (["--sync-level", "0.41", "--pixel", "25"], "source type 00"),
    (["--sync-level", "1.0", "--pixel", "25", "--level-field-proven"], "source type 00"),
    (["--s2", "--source-type", "07"], "source type 00"),
    (["--s2-header", "--source-type", "07", "--pixel", "25"], "source type 00"),
    (["--source-type", "00", "--sync-level", "1.0", "--pixel", "128"], "25"),
    (["--source-type", "00", "--sync-level", "1.0", "--pixel", "128", "--level-field-proven"], "25"),
    (["--bytes16", "ffffff", "--pixel", "128"], "25"),
    (["--byte26", "01", "--pixel", "128"], "25"),
    (["--declared-rate", "013c", "--pixel", "128"], "25"),
    (["--counter", "on", "--pixel", "128"], "25"),
    (["--row-tail", "0000", "--pixel", "128"], "25"),
    (["--sync-len", "1036", "--pixel", "26"], "25"),
    (["--pixel", "-1"], "128"),
    (["--s2", "--pixel", "128", "--level-field-proven"], "25"),          # the S2's level is 0xff
    (["--s2", "--sync-level", "0.1", "--pixel", "128"], "25"),
    (["--pixel", "129"], "128"),
    (["--fps", "14"], "fps"),
    (["--fps", "241"], "fps"),
    (["--seconds", "61"], "seconds"),
    (["--tail-seconds", "6"], "tail"),
    (["--sync-reps", "0"], "sync"),
    (["--sync-reps", "4"], "sync"),
    (["--bright-reps", "3"], "bright"),
    (["--sync-len", "60"], "112 or 1036"),
    (["--sync-len", "1515"], "112 or 1036"),
    (["--sync-len", "500"], "112 or 1036"),
    (["--jitter-ms", "6"], "jitter"),
    (["--order", "sync-rows", "--gap-ms", "5"], "gap"),
    (["--gap-ms", "16"], "period"),                                       # 16 + rows does not fit in 16.7
    (["--fps", "120", "--gap-ms", "5", "--jitter-ms", "3"], "period"),
    # a field takes the values seen on the wire, and the brief's, and no other
    (["--row-tail", "00"], "0888 or 0000"),
    (["--row-tail", "ffff"], "0888 or 0000"),
    (["--row-tail", "0880"], "0888 or 0000"),
    (["--declared-rate", "3c"], "0000, 013c or 011e"),
    (["--declared-rate", "0114"], "0000, 013c or 011e"),
    (["--bytes16", "ff"], "000000 or ffffff"),
    (["--bytes16", "010203"], "000000 or ffffff"),
    (["--source-type", "01"], "00 or 07"),
    (["--source-type", "zz"], "00 or 07"),
    (["--byte26", "02"], "00 or 01"),
    (["--byte36", "ff"], "00 or 05"),
    # numbers are numbers
    (["--fps", "nan"], "fps"),
    (["--fps", "inf"], "fps"),
    (["--seconds", "nan"], "seconds"),
    (["--seconds", "inf"], "seconds"),
    (["--tail-seconds", "nan"], "tail"),
    (["--gap-ms", "nan"], "gap"),
    (["--gap-ms", "-1"], "gap"),
    (["--jitter-ms", "nan"], "jitter"),
    (["--jitter-ms", "-0.5"], "jitter"),
    (["--spin-ms", "nan"], "spin"),
    (["--brightness", "nan"], "brightness"),
    (["--brightness", "-0.1"], "brightness"),
    (["--sync-level", "nan"], "sync-level"),
    (["--bright-level", "nan"], "bright-level"),
])
def test_what_the_safety_rules_forbid_is_refused(argv, words):
    with pytest.raises(ValueError, match=words):
        send.plan_from(argv)


def test_the_cap_is_lifted_only_by_the_owners_flag_and_a_level_within_the_cap():
    plan = send.plan_from(["--s2", "--sync-level", "0.1", "--pixel", "128", "--level-field-proven"])
    assert plan.pixel == 128 and plan.sync.level == 25


def test_the_owners_flag_alone_does_not_brighten_the_picture():
    assert send.plan_from(["--s2", "--sync-level", "0.1", "--level-field-proven"]).pixel == 128
    assert send.plan_from(["--s2", "--level-field-proven"]).pixel == 25


def test_there_is_no_flag_for_byte_37():
    # its meaning is not known; the S2 sets it every 4 s. Not sent without the owner's word and a code change.
    with pytest.raises(SystemExit):
        send.plan_from(["--mark37-every", "241"])


def test_describe_names_the_owners_flag():
    text = send.describe(send.plan_from(["--s2", "--sync-level", "0.1", "--level-field-proven"]))
    assert "level field proven" in text and "pixel 128" in text
    assert "level field proven" not in send.describe(send.plan_from(["--s2"]))


def test_the_hex_flags_take_either_case():
    assert send.plan_from(["--bytes16", "FFFFFF"]).sync.bytes16 == b"\xff\xff\xff"
    assert send.plan_from(["--declared-rate", "013C"]).sync.declared_rate == b"\x01\x3c"


def test_describe_names_every_variable_that_left_the_base():
    text = send.describe(send.plan_from(["--s2", "--fps", "60.32"]))
    for word in ("source type 0x00", "counter", "1036", "sync x1", "no brightness packet", "00 00",
                 "sync-rows", "60.32", "pixel 25"):
        assert word in text, word
