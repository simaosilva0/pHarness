"""Box files, connectors and pins (STRUCT.md, boxes; CONFIG.md: Boxes,
connectors, devices, boards)."""

NOSE = "boxes/nose.yaml"
BULKHEAD = "boxes/bulkhead.yaml"


# --- the box -------------------------------------------------------------------

def test_a_box_without_a_name(project):
    project.replace(NOSE, "box: Nose\n", "")
    assert project.broken() == [("box-fields", "boxes/nose.yaml:1")]


def test_a_box_without_connectors(project):
    project.write(NOSE, "box: Nose\n")
    assert ("box-fields", "boxes/nose.yaml:1") in project.broken()


def test_a_board_pin_in_a_box_without_boards(project):
    project.replace(NOSE, "boards: [front_io]\n", "")
    assert project.broken() == [("box-fields", "boxes/nose.yaml:1")]


def test_a_box_with_only_pass_pins_needs_no_boards(project):
    assert "boards" not in (project.root / BULKHEAD).read_text()
    assert project.broken() == []


def test_a_box_name_in_another_style(project):
    project.replace(NOSE, "box: Nose\n", "box: nose\n")
    assert ("box-style", "boxes/nose.yaml:1") in project.broken()


def test_a_box_in_a_file_named_otherwise(project):
    project.replace(NOSE, "box: Nose\n", "box: Nose Cone\n")
    assert ("box-file", "boxes/nose.yaml:1") in project.broken()


def test_a_board_name_in_another_style(project):
    project.replace(NOSE, "boards: [front_io]\n", "boards: [front_io, Steering]\n")
    assert project.broken() == [("board-style", "boxes/nose.yaml:2")]


def test_a_box_named_like_its_board(project):
    project.replace(NOSE, "boards: [front_io]\n", "boards: [front_io, nose]\n")
    assert project.broken() == [("box-not-board", "boxes/nose.yaml:2")]


# --- connectors ----------------------------------------------------------------

def test_a_connector_name_in_another_style(project):
    project.replace(NOSE, "  bots:\n", "  Bots:\n")
    assert project.broken() == [("connector-style", "boxes/nose.yaml:36")]


def test_a_connector_without_pins(project):
    project.add(NOSE, "  spare-io:\n    part: DT06-2S\n")
    assert project.broken() == [("connector-pins", "boxes/nose.yaml:75")]


# --- pins ----------------------------------------------------------------------

def test_a_pin_written_twice(project):
    project.replace(NOSE, "{pin: '12', type: spare}", "{pin: '11', type: spare}")
    assert project.broken() == [("pin-once", "boxes/nose.yaml:20")]


def test_pins_in_another_case_are_two_pins(project):
    project.replace(NOSE, "{pin: J, type: spare}", "{pin: j, type: spare}")
    project.add(NOSE, "      - {pin: J, type: spare}\n")
    assert project.broken() == []


def test_a_pin_without_a_type(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: '10'}")
    assert project.broken() == [("pin-fields", "boxes/nose.yaml:18")]


def test_a_pin_that_is_not_a_string(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: 10, type: spare}")
    assert project.broken() == [("pin-string", "boxes/nose.yaml:18")]


def test_a_spare_pin_with_a_net(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: '10', net: bpps, type: spare}")
    assert project.broken() == [("pin-net", "boxes/nose.yaml:18")]


def test_a_pin_without_a_net(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: '10', type: analog}")
    assert project.broken() == [("pin-net", "boxes/nose.yaml:18")]


def test_an_unfitted_pin_without_a_note(project):
    project.replace(NOSE, "type: unfitted, note: 'second brake pressure sensor, dropped'}",
                    "type: unfitted}")
    assert project.broken() == [("unfitted-note", "boxes/nose.yaml:19")]


def test_fields_out_of_order(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{type: spare, pin: '10'}")
    report = project.check()
    assert [(p.rule, p.level, p.entry) for p in report.problems] == [("pin-order", "warn", "Nose.pedals.10")]


def test_a_to_that_is_no_box_or_device(project):
    project.replace(NOSE, "{pin: '1', net: sdc, type: chain:s4, to: BOTS}",
                    "{pin: '1', net: sdc, type: chain:s4, to: Bots}")
    assert ("to-known", "boxes/nose.yaml:39") in project.broken()


def test_a_to_its_own_box(project):
    project.replace(NOSE, "{pin: H, net: sdc, type: chain:s4, to: Bulkhead}",
                    "{pin: H, net: sdc, type: chain:s4, to: Nose}")
    assert ("to-not-own-box", "boxes/nose.yaml:73") in project.broken()


def test_a_spare_pin_with_a_to(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: '10', type: spare, to: BPPS}")
    assert project.broken() == [("spare-no-to", "boxes/nose.yaml:18")]


def test_an_at_without_a_board(project):
    project.replace(NOSE, "at: front_io:a0}", "at: a0}")
    assert project.broken() == [("at-form", "boxes/nose.yaml:11")]


def test_an_at_on_a_board_the_box_does_not_have(project):
    project.replace(NOSE, "at: front_io:a0}", "at: rear_io:a0}")
    assert project.broken() == [("at-form", "boxes/nose.yaml:11")]


def test_a_pass_with_nothing_to_pass_to(project):
    project.replace(NOSE, "{pin: '1', net: imu, type: power:12v, to: IMU}",
                    "{pin: '1', net: imu, type: power:12v, to: IMU, at: pass}")
    project.replace(NOSE, "{pin: C, net: imu, type: power:12v, to: Bulkhead}",
                    "{pin: C, type: spare}")
    assert ("at-pass", "boxes/nose.yaml:58") in project.broken()


def test_a_pass_to_another_connector(project):
    project.replace(NOSE, "{pin: '1', net: imu, type: power:12v, to: IMU}",
                    "{pin: '1', net: imu, type: power:12v, to: IMU, at: pass}")
    assert project.broken() == []
