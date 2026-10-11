"""Conductors and routes: what the pins add up to across boxes (CONFIG.md: the
start, Labels, Chains; STRUCT.md: car.yaml, boxes)."""

import re
import shutil

CAR = "car.yaml"
NOSE = "boxes/nose.yaml"
BATTERY = "boxes/battery.yaml"
REARHUB = "boxes/rearhub.yaml"
BULKHEAD = "boxes/bulkhead.yaml"


def problems(project):
    """The problems with their level and entry: [(rule, where, level, entry)]."""
    report = project.check()
    return [(p.rule, p.where, p.level, p.entry) for p in report.sorted_problems()]


# --- conductors ----------------------------------------------------------------

def test_a_conductor_on_one_pin(project):
    project.replace(NOSE, "{pin: '2', type: spare}", "{pin: '2', net: horn, type: digital}")
    assert problems(project) == [("conductor-one-end", "boxes/nose.yaml:43", "warn", "horn digital")]


def test_a_conductor_on_one_pin_going_to_a_device(project):
    project.replace(NOSE, "{pin: '2', type: spare}", "{pin: '2', net: horn, type: digital, to: BOTS}")
    assert project.broken() == []


def test_a_shield_on_one_pin(project):
    assert "{pin: '3', net: fl_wheel_speed, type: shield}" in (project.root / NOSE).read_text()
    assert project.broken() == []


def test_two_conductors_with_one_label(project):
    project.replace(NOSE, "{pin: '10', type: spare}", "{pin: '10', net: apps1, type: digital, to: APPS1}")
    assert project.broken() == [("label-unique", "boxes/nose.yaml:12")]


# --- where the wires go ----------------------------------------------------------

def test_a_to_a_box_without_the_pin(project):
    project.replace(BATTERY, "{pin: '1', net: bms, type: power:12v, to: RearHub}",
                    "{pin: '1', net: bms, type: power:12v, to: Nose}")
    # Its cable does not go to Nose either.
    assert problems(project) == [("to-reaches", "boxes/battery.yaml:10", "error", "Battery.lv.1"),
                                 ("cable-on-end", "boxes/battery.yaml:10", "error", None)]


# --- buses and links -----------------------------------------------------------------

def test_an_end_that_is_no_box_or_device(project):
    project.replace(CAR, "ends: [Battery, Charger]", "ends: [Battery, Charger Port]")
    assert project.broken() == [("ends-known", "car.yaml:40")]


def test_a_box_the_bus_lands_in_missing_from_its_ends(project):
    project.replace(CAR, "ends: [Nose, Cockpit, RearHub, IMU]", "ends: [Nose, RearHub, IMU]")
    assert problems(project) == [("ends-match", "car.yaml:39", "error", "can_chassis")]


def test_an_end_the_bus_does_not_land_in(project):
    project.replace(CAR, "ends: [Cockpit, Steering Wheel]", "ends: [Cockpit, Steering Wheel, Nose]")
    assert project.broken() == [("ends-match", "car.yaml:41")]


def test_a_bus_that_only_passes_through_a_box(project):
    assert "Bulkhead" not in (project.root / CAR).read_text()
    assert "can_chassis" in (project.root / "boxes/bulkhead.yaml").read_text()
    assert project.broken() == []


def test_an_internal_bus(project):
    project.replace(CAR, "\nlinks:\n", "  can_motor: {bitrate: 500000, ends: [Inverter], internal: true}\n\nlinks:\n")
    assert project.broken() == []


def test_an_internal_bus_with_two_ends(project):
    project.replace(CAR, "ends: [Battery, Charger]}", "ends: [Battery, Charger], internal: true}")
    assert problems(project) == [("bus-internal", "car.yaml:40", "error", "can_charge")]


def test_a_bus_alone_in_its_box_not_marked_internal(project):
    project.replace(CAR, "\nlinks:\n", "  can_motor: {bitrate: 500000, ends: [Inverter]}\n\nlinks:\n")
    assert project.broken() == [("bus-internal", "car.yaml:45")]


def test_a_bus_without_ends(project):
    project.replace(CAR, "can_charge: {bitrate: 250000, ends: [Battery, Charger]}", "can_charge: {bitrate: 250000}")
    assert project.broken() == [("bus-fields", "car.yaml:40")]


# --- devices -------------------------------------------------------------------------

def test_a_device_nothing_uses(project):
    project.replace(CAR, "  APPS2: {}\n", "  APPS2: {}\n  Horn: {}\n")
    assert problems(project) == [("device-used", "car.yaml:6", "warn", "Horn")]


# --- chains --------------------------------------------------------------------------

def test_a_chain_out_on_no_pin(project):
    project.replace(CAR, "    - {node: TSMS, out: s8}\n", "    - {node: TSMS, out: s8}\n    - {node: Brake Light, out: s9}\n")
    # s8 now has to reach Brake Light too.
    assert problems(project) == [("chain-order", "car.yaml:59", "error", "sdc chain:s8"),
                                 ("chain-out-used", "car.yaml:60", "warn", "sdc chain:s9")]


def test_a_chain_out_to_the_wrong_node(project):
    # s0 runs from the left button to the right one, not to TSMS.
    project.replace(REARHUB, "{pin: '3', net: sdc, type: chain:s0, to: Right Shutdown Button}",
                    "{pin: '3', net: sdc, type: chain:s0, to: TSMS}")
    assert problems(project) == [("chain-order", "car.yaml:51", "error", "sdc chain:s0")]


def test_a_chain_out_in_two_pieces(project):
    # No wire between the RearHub and the Bulkhead: s1 leaves the right button
    # and reaches the cockpit button, but the two are not joined.
    project.replace(REARHUB, "{pin: J, net: sdc, type: chain:s1, to: Bulkhead, cable: Rear Signal, at: pass}",
                    "{pin: J, type: spare}")
    project.replace(BULKHEAD, "{pin: J, net: sdc, type: chain:s1, to: RearHub, cable: Rear Signal, at: pass}",
                    "{pin: J, type: spare}")
    project.replace(REARHUB, "type: chain:s1, to: Right Shutdown Button, at: pass}",
                    "type: chain:s1, to: Right Shutdown Button}")
    project.replace(BULKHEAD, "type: chain:s1, to: Cockpit, at: pass}", "type: chain:s1, to: Cockpit}")
    assert problems(project) == [("chain-order", "car.yaml:52", "error", "sdc chain:s1")]


def test_a_chain_out_that_misses_its_node_in_a_box(project):
    # The BSPD moves to the Nose: s4 lands there, but s5 never does.
    project.replace(CAR, "{node: BSPD, out: s5, box: RearHub}", "{node: BSPD, out: s5, box: Nose}")
    assert problems(project) == [("chain-order", "car.yaml:56", "error", "sdc chain:s5")]


def test_without_cables_the_chain_order_waits(project):
    # A stretch from one device to another is only written in a cable.
    shutil.rmtree(project.root / "cables")
    for path in (project.root / "boxes").glob("*.yaml"):
        text = re.sub(r"\n    cable: [^\n]*", "", path.read_text())
        path.write_text(re.sub(r", cable: [^,}]*", "", text))
    project.replace(REARHUB, "{pin: '3', net: sdc, type: chain:s0, to: Right Shutdown Button}",
                    "{pin: '3', net: sdc, type: chain:s0, to: TSMS}")
    assert project.broken() == []


def test_a_chain_out_with_a_broken_to_is_not_followed(project):
    project.replace(NOSE, "{pin: '1', net: sdc, type: chain:s4, to: BOTS}",
                    "{pin: '1', net: sdc, type: chain:s4, to: Bots}")
    assert "chain-order" not in [rule for rule, _ in project.broken()]


def test_a_chain_out_inside_one_box(project):
    # IMD and BMS are both in the Battery: s6 runs inside it, on no pin.
    for file in (project.root / "boxes").iterdir():
        assert "chain:s6" not in file.read_text()
    assert project.broken() == []

