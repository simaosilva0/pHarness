"""The pinout tables, as rows (pinout.py)."""

from pharness.check import read_and_check
from pharness.project.labels import wire_label
from pharness.output.pinout import build_pinout

NOSE = "boxes/nose.yaml"


def pinout_of(project):
    report, model = read_and_check(project.root)
    assert report.errors() == []
    return build_pinout(model, report)


def box(pinout, name):
    for one in pinout.boxes:
        if one.name == name:
            return one
    raise AssertionError(f"no box {name}")


def connector(pinout, box_name, name):
    for one in box(pinout, box_name).connectors:
        if one.name == name:
            return one
    raise AssertionError(f"no connector {box_name} {name}")


def row(pinout, box_name, connector_name, pin):
    for one in connector(pinout, box_name, connector_name).rows:
        if one.pin == pin:
            return one
    raise AssertionError(f"no pin {box_name} {connector_name} {pin}")


# --- what is in it -----------------------------------------------------------------

def test_every_box_connector_and_pin_once(project):
    report, model = read_and_check(project.root)
    pinout = build_pinout(model, report)

    assert pinout.car == "Kestrel"
    assert [one.file for one in pinout.boxes] == [one.file for one in model.boxes]
    assert pinout.connector_count() == sum(len(one.connectors) for one in model.boxes)
    assert pinout.pin_count() == len(list(model.pins()))


def test_a_box_keeps_its_boards_note_and_connector_parts(project):
    pinout = pinout_of(project)
    battery = box(pinout, "Battery")
    assert battery.boards == ["bms"]
    assert battery.note.startswith("the accumulator")
    assert [one.name for one in battery.connectors] == ["lv", "hv", "charge"]
    assert connector(pinout, "Battery", "lv").part == "DT06-8S"


def test_pins_stay_in_file_order(project):
    pinout = pinout_of(project)
    rows = connector(pinout, "Battery", "lv").rows
    assert [one.pin for one in rows] == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_a_box_without_boards(project):
    pinout = pinout_of(project)
    assert box(pinout, "Bulkhead").boards == []
    assert row(pinout, "Bulkhead", "nose", "A").at == "pass"


# --- one row ---------------------------------------------------------------------

def test_a_row_has_the_pin_fields(project):
    one = row(pinout_of(project), "Battery", "lv", "5")
    assert (one.net, one.type, one.to, one.at, one.note) == ("sdc", "chain:s5", "RearHub", None, "into the IMD relay")


def test_wire_labels_by_label_and_by_qualifier(project):
    pinout = pinout_of(project)
    assert row(pinout, "Battery", "lv", "1").wire == "bms_12v"
    assert row(pinout, "Battery", "lv", "2").wire == "bms_gnd"
    assert row(pinout, "Battery", "lv", "3").wire == "can_drive_h"
    assert row(pinout, "Battery", "lv", "5").wire == "sdc_s5"


def test_wire_labels_in_another_net_style(project):
    report, model = read_and_check(project.root)
    model.settings.style["net"] = "upper_kebab"
    assert wire_label(model.settings, "CAN-DRIVE", "can:H") == "CAN-DRIVE-H"
    assert wire_label(model.settings, "BMS", "ground") == "BMS-gnd"


def test_spare_and_unfitted_pins_are_unused_with_no_wire(project):
    pinout = pinout_of(project)
    spare = row(pinout, "Battery", "lv", "8")
    unfitted = row(pinout, "Nose", "pedals", "11")
    assert (spare.unused, spare.wire) == (True, None)
    assert (unfitted.unused, unfitted.wire) == (True, None)
    assert unfitted.note == "second brake pressure sensor, dropped"
    assert row(pinout, "Battery", "lv", "1").unused is False


def test_to_a_box_or_to_a_device(project):
    pinout = pinout_of(project)
    assert row(pinout, "Battery", "lv", "1").to_is_box is True
    assert row(pinout, "Nose", "imu", "1").to_is_box is False


# --- warnings --------------------------------------------------------------------

def test_a_warning_is_listed_and_on_its_pin(project):
    project.replace(NOSE, "{pin: '2', type: spare}", "{pin: '2', net: horn, type: digital}")
    pinout = pinout_of(project)

    assert [(w.rule, w.where) for w in pinout.warnings] == [("conductor-one-end", "boxes/nose.yaml:43")]
    horn = row(pinout, "Nose", "bots", "2")
    assert [w.rule for w in horn.warnings] == ["conductor-one-end"]
    assert row(pinout, "Nose", "bots", "1").warnings == []


# --- cables and colors -----------------------------------------------------------

def cable(pinout, name):
    for one in pinout.cables:
        if one.name == name:
            return one
    raise AssertionError(f"no cable {name}")


def test_a_row_knows_its_cable_far_pin_and_color(project):
    one = row(pinout_of(project), "RearHub", "front", "G")
    assert (one.cable, one.far, one.far_where) == ("Rear Signal", "Bulkhead.rear.G", "boxes/bulkhead.yaml:37")
    assert (one.color, one.color_picked) == ("yellow", True)


def test_a_row_to_a_device_has_no_far_pin(project):
    one = row(pinout_of(project), "Nose", "imu", "1")
    assert (one.to, one.far, one.cable) == ("IMU", None, "IMU Lead")


def test_a_spare_pin_has_no_color(project):
    one = row(pinout_of(project), "Battery", "lv", "8")
    assert (one.cable, one.color) == (None, None)


def test_a_pin_color_is_on_both_ends_of_its_wire(project):
    project.replace("boxes/bulkhead.yaml", "to: RearHub, cable: Rear Power, at: pass}\n      - {pin: B",
                    "to: RearHub, cable: Rear Power, color: blue, at: pass}\n      - {pin: B")
    pinout = pinout_of(project)
    assert (row(pinout, "Bulkhead", "rear", "A").color, row(pinout, "Bulkhead", "rear", "A").color_picked) == ("blue", False)
    assert row(pinout, "RearHub", "front", "A").color == "blue"


def test_every_wire_once(project):
    pinout = pinout_of(project)
    assert len(pinout.cables) == 28
    assert pinout.wire_count() == 150
    rear = cable(pinout, "Rear Signal")
    assert [(w.start, w.end) for w in rear.wires] == [
        ("Bulkhead.rear.G", "RearHub.front.G"), ("Bulkhead.rear.H", "RearHub.front.H"),
        ("Bulkhead.rear.J", "RearHub.front.J"), ("Bulkhead.rear.K", "RearHub.front.K")]


def test_a_wire_to_a_device(project):
    pedals = cable(pinout_of(project), "Pedals")
    first = pedals.wires[0]
    assert (first.start, first.end, first.end_where, first.wire) == ("Nose.pedals.1", "APPS1", None, "apps1_gnd")


def test_a_listed_wire(project):
    project.write("cables/hoop_link.yaml", """cable: Hoop Link
ends: [Left Shutdown Button, Right Shutdown Button]
wires:
  - {net: sdc, type: chain:s0, from: Left Shutdown Button, to: Right Shutdown Button, color: white}
""")
    wire = cable(pinout_of(project), "Hoop Link").wires[0]
    assert (wire.start, wire.end, wire.wire, wire.color, wire.color_picked) == (
        "Left Shutdown Button", "Right Shutdown Button", "sdc_s0", "white", False)


def test_the_legend_has_each_type_once_and_a_chain_as_one(project):
    legend = pinout_of(project).colors
    types = [one.type for one in legend]
    assert len(types) == len(set(types))
    assert "chain:*" in types
    assert not any(t.startswith("chain:s") for t in types)
    assert "shield" not in types


# --- chain taps --------------------------------------------------------------------

REARHUB = "boxes/rearhub.yaml"
CONFIG = "config.yaml"
HOOP_LINK = """cable: Hoop Link
ends: [Left Shutdown Button, Right Shutdown Button]
wires:
  - {net: sdc, type: chain:s0, from: Left Shutdown Button, to: Right Shutdown Button}
"""


def tap_s0(project):
    """s0 runs from button to button in its own cable; the RearHub only senses
    it, with a wire to the left button: that wire is a tap."""
    project.write("cables/hoop_link.yaml", HOOP_LINK)
    project.replace(REARHUB, "{pin: '2', net: sdc, type: chain:s0, to: Left Shutdown Button}",
                    "{pin: '2', net: sdc, type: chain:s0, to: Left Shutdown Button, at: vcu:in0}")
    project.replace(REARHUB, "{pin: '3', net: sdc, type: chain:s0, to: Right Shutdown Button}",
                    "{pin: '3', type: spare}")
    assert project.broken() == []


def test_a_wire_that_taps_a_chain(project):
    tap_s0(project)
    pinout = pinout_of(project)
    sense = row(pinout, "RearHub", "sdc", "2")
    assert (sense.color, sense.color_picked) == ("brown/white", True)
    loop = cable(pinout, "Hoop Link").wires[0]
    assert (loop.color, loop.tap) == ("brown", False)
    tap = [wire for wire in cable(pinout, "Main Hoop").wires if wire.start == "RearHub.sdc.2"][0]
    assert (tap.color, tap.tap) == ("brown/white", True)


def test_the_legend_has_the_tap_color(project):
    tap_s0(project)
    legend = [(one.type, one.color, one.tap) for one in pinout_of(project).colors]
    assert ("chain:*", "brown", False) in legend
    assert ("chain:*", "brown/white", True) in legend


def test_without_stripes_a_tap_is_brown(project):
    tap_s0(project)
    project.replace(CONFIG, "palette: striped\n", "palette: solid\n")
    pinout_of_solid = pinout_of(project)
    assert row(pinout_of_solid, "RearHub", "sdc", "2").color == "brown"


def test_a_chosen_chain_color_is_on_its_taps_too(project):
    tap_s0(project)
    project.replace(CONFIG, "color: auto\n", "color: fill\ncolors:\n  chain:s0: white\n")
    pinout = pinout_of(project)
    assert row(pinout, "RearHub", "sdc", "2").color == "white"
    assert cable(pinout, "Hoop Link").wires[0].color == "white"


def test_kestrel_has_no_taps(project):
    for one in pinout_of(project).cables:
        assert not any(wire.tap for wire in one.wires)
