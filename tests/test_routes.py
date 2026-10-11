"""Conductors and routes: what the pins add up to across boxes (CONFIG.md: the
start, Labels, Chains; STRUCT.md: car.yaml, boxes)."""

CAR = "car.yaml"
NOSE = "boxes/nose.yaml"
BATTERY = "boxes/battery.yaml"


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
    assert problems(project) == [("chain-out-used", "car.yaml:60", "warn", "sdc chain:s9")]


def test_a_chain_out_inside_one_box(project):
    # IMD and BMS are both in the Battery: s6 runs inside it, on no pin.
    for file in (project.root / "boxes").iterdir():
        assert "chain:s6" not in file.read_text()
    assert project.broken() == []

