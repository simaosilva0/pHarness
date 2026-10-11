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

    assert [(w.rule, w.where) for w in pinout.warnings] == [("conductor-one-end", "boxes/nose.yaml:40")]
    horn = row(pinout, "Nose", "bots", "2")
    assert [w.rule for w in horn.warnings] == ["conductor-one-end"]
    assert row(pinout, "Nose", "bots", "1").warnings == []
