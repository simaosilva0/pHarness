"""cables/<cable>.yaml, and the `cable` of connectors and pins (STRUCT.md,
cables; CONFIG.md, Boxes, connectors, devices, boards, cables)."""

import re
import shutil

from pharness.check import read_and_check

CONFIG = "config.yaml"
NOSE = "boxes/nose.yaml"
REARHUB = "boxes/rearhub.yaml"
BULKHEAD = "boxes/bulkhead.yaml"
LEFT_COOLING = "cables/left_cooling.yaml"

LOOP = """cable: Hoop Link
ends: [Left Shutdown Button, Right Shutdown Button]
wires:
  - {net: sdc, type: chain:s0, from: Left Shutdown Button, to: Right Shutdown Button}
"""


def problems(project):
    """The problems with their level and entry: [(rule, where, level, entry)]."""
    report = project.check()
    return [(p.rule, p.where, p.level, p.entry) for p in report.sorted_problems()]


# --- the cable -----------------------------------------------------------------

def test_a_cable_without_ends(project):
    project.replace(LEFT_COOLING, "ends: [RearHub.cooling, Left Pump, Left Fan]\n", "")
    assert project.broken() == [("cable-fields", "cables/left_cooling.yaml:1")]


def test_a_cable_name_in_another_style(project):
    project.write("cables/hoop_link.yaml", LOOP.replace("Hoop Link", "hoop link"))
    assert project.broken() == [("cable-style", "cables/hoop_link.yaml:1")]


def test_a_cable_in_the_wrong_file(project):
    project.write("cables/hoop-link.yaml", LOOP)
    assert project.broken() == [("cable-file", "cables/hoop-link.yaml:1")]


def test_a_cable_with_one_end(project):
    project.write("cables/hoop_link.yaml", "cable: Hoop Link\nends: [IMU]\n")
    assert ("cable-ends", "cables/hoop_link.yaml:2") in project.broken()


def test_an_end_written_twice(project):
    project.replace(LEFT_COOLING, "Left Pump, Left Fan]", "Left Pump, Left Fan, Left Pump]")
    assert project.broken() == [("cable-ends", "cables/left_cooling.yaml:2")]


def test_an_end_that_is_no_connector_or_device(project):
    project.replace(LEFT_COOLING, "[RearHub.cooling,", "[RearHub.Cooling,")
    # The pins on it are not judged against the misspelled end.
    assert project.broken() == [("cable-ends", "cables/left_cooling.yaml:2")]


# --- listed wires ----------------------------------------------------------------

def test_a_wire_between_two_devices(project):
    project.write("cables/hoop_link.yaml", LOOP)
    assert project.broken() == []


def test_a_wire_without_a_far_end(project):
    project.write("cables/hoop_link.yaml", LOOP.replace(", to: Right Shutdown Button", ""))
    assert project.broken() == [("wire-fields", "cables/hoop_link.yaml:4")]


def test_a_wire_to_a_device_that_is_no_end(project):
    project.write("cables/hoop_link.yaml", LOOP.replace("to: Right Shutdown Button", "to: TSMS"))
    assert project.broken() == [("wire-fields", "cables/hoop_link.yaml:4")]


def test_a_wire_net_is_checked_like_any_net(project):
    project.write("cables/hoop_link.yaml", LOOP.replace("net: sdc", "net: SDC"))
    assert ("net-style", "cables/hoop_link.yaml:4") in project.broken()


def test_a_listed_wire_carries_a_chain_out(project):
    project.replace(REARHUB, "{pin: '2', net: sdc, type: chain:s0, to: Left Shutdown Button}",
                    "{pin: '2', type: spare}")
    project.replace(REARHUB, "{pin: '3', net: sdc, type: chain:s0, to: Right Shutdown Button}",
                    "{pin: '3', type: spare}")
    project.write("cables/hoop_link.yaml", LOOP)
    assert project.broken() == []


# --- connectors and pins ---------------------------------------------------------

def test_a_pin_on_a_cable_that_does_not_exist(project):
    project.replace(REARHUB, "to: Left Pump, cable: Left Cooling, at: vcu:out6",
                    "to: Left Pump, cable: Left Coolin, at: vcu:out6")
    assert project.broken() == [("cable-known", "boxes/rearhub.yaml:62")]


def test_a_connector_on_a_cable_that_does_not_exist(project):
    project.replace(NOSE, "    cable: Pedals\n", "    cable: Pedal\n")
    # Once, on the connector, not on each of its pins.
    assert project.broken() == [("cable-known", "boxes/nose.yaml:6")]


def test_a_cable_on_a_pin_without_a_to(project):
    project.replace(NOSE, "{pin: '3', net: fl_wheel_speed, type: shield}",
                    "{pin: '3', net: fl_wheel_speed, type: shield, cable: Chassis}")
    assert project.broken() == [("cable-to", "boxes/nose.yaml:28")]


def test_a_cable_on_a_spare_pin(project):
    project.replace(REARHUB, "{pin: '7', type: spare}\n      - {pin: '8', type: spare}\n  battery:",
                    "{pin: '7', type: spare, cable: Main Hoop}\n      - {pin: '8', type: spare}\n  battery:")
    assert project.broken() == [("spare-no-to", "boxes/rearhub.yaml:35")]


def test_a_pin_on_a_cable_that_does_not_go_where_it_goes(project):
    project.replace(REARHUB, "to: Left Pump, cable: Left Cooling, at: vcu:out6",
                    "to: Left Pump, cable: Right Cooling, at: vcu:out6")
    assert project.broken() == [("cable-on-end", "boxes/rearhub.yaml:62")]


def test_a_connector_on_a_cable_that_does_not_end_there(project):
    project.replace(NOSE, "    cable: Pedals\n", "    cable: Chassis\n")
    assert project.broken() == [("cable-on-end", "boxes/nose.yaml:6")]


def test_two_ends_of_a_wire_on_different_cables(project):
    project.replace(BULKHEAD, "{pin: G, net: can_chassis, type: can:h, to: RearHub, cable: Rear Signal",
                    "{pin: G, net: can_chassis, type: can:h, to: RearHub, cable: Rear Power")
    # Either end may be the wrong one, so both are reported.
    assert project.broken() == [("cable-far-pin", "boxes/bulkhead.yaml:37"),
                                ("cable-far-pin", "boxes/rearhub.yaml:21")]


# --- every wire on a cable ---------------------------------------------------------

def test_a_pin_on_no_cable(project):
    project.replace(NOSE, "    cable: IMU Lead\n", "")
    assert problems(project) == [
        ("to-cabled", "boxes/nose.yaml:63", "warn", "Nose.imu.1"),
        ("to-cabled", "boxes/nose.yaml:64", "warn", "Nose.imu.2"),
        ("to-cabled", "boxes/nose.yaml:65", "warn", "Nose.imu.3"),
        ("to-cabled", "boxes/nose.yaml:66", "warn", "Nose.imu.4"),
        ("cable-used", "cables/imu_lead.yaml:1", "warn", "IMU Lead"),
    ]


def test_a_pin_on_no_cable_accepted(project):
    project.replace(NOSE, "    cable: IMU Lead\n", "")
    project.remove("cables/imu_lead.yaml")
    project.replace(CONFIG, "accept: {}\n", "accept:\n  to-cabled:\n    Nose.imu.1: not routed yet\n")
    assert [p.entry for p in project.check().problems] == ["Nose.imu.2", "Nose.imu.3", "Nose.imu.4"]


def test_without_cables_nothing_needs_one(project):
    shutil.rmtree(project.root / "cables")
    for path in (project.root / "boxes").glob("*.yaml"):
        text = re.sub(r"\n    cable: [^\n]*", "", path.read_text())
        path.write_text(re.sub(r", cable: [^,}]*", "", text))
    assert project.broken() == []


def test_an_unread_cable_file_is_reported_once(project):
    project.write(LEFT_COOLING, "cable: Left Cooling\nends: [\n")
    assert project.broken_rules() == ["yaml"]


# --- twisted pairs -------------------------------------------------------------------

def test_a_pair_split_across_two_cables(project):
    # can:l moves to Rear Power at both ends: the wire is sound, the pair is not.
    project.replace(REARHUB, "{pin: H, net: can_chassis, type: can:l, to: Bulkhead, cable: Rear Signal",
                    "{pin: H, net: can_chassis, type: can:l, to: Bulkhead, cable: Rear Power")
    project.replace(BULKHEAD, "{pin: H, net: can_chassis, type: can:l, to: RearHub, cable: Rear Signal",
                    "{pin: H, net: can_chassis, type: can:l, to: RearHub, cable: Rear Power")
    assert problems(project) == [
        ("pair-cable", "boxes/bulkhead.yaml:37", "warn", "Bulkhead.rear.G"),
        ("pair-cable", "boxes/rearhub.yaml:21", "warn", "RearHub.front.G"),
    ]


def test_hv_is_no_twisted_pair(project):
    # HV+ and HV- run as two single cables.
    _, model = read_and_check(project.root)
    pairs = model.settings.twisted_pairs()
    assert ("can:h", "can:l") in pairs
    assert ("analog:p", "analog:n") in pairs
    assert not any(first.startswith("hv:") for first, _ in pairs)
