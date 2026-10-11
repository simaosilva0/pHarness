"""boxes/<box>.yaml (STRUCT.md, boxes; CONFIG.md: Boxes, connectors, devices, boards)."""

import re

from ..project.fields import where
from ..project.read import PIN_FIELDS
from .names import check_style


def check_boxes(model, nets, report):
    for box in model.boxes:
        check_box(model, box, report)
        for connector in box.connectors:
            check_connector(model, box, connector, report)
            for pin in connector.pins:
                check_pin(model, box, pin, nets, report)


# --- the box -------------------------------------------------------------------

def check_box(model, box, report):
    """box-fields, box-style, box-file, board-style, box-not-board."""
    style = model.settings.style
    problems = box_field_problems(box)
    report.check("box-fields", not problems, f"{box.file}:{box.data.line}", f"box: {'; '.join(problems)}")

    if box.name is not None:
        at = where(box.file, box.data, "box")
        check_style(report, "box-style", box.name, style["box"], at, "box")
        expected = file_name(box.name)
        report.check("box-file", box.path.name == expected, at,
                     f"box {box.name} is in {box.path.name}, not {expected}")

    for board in box.boards:
        at = where(box.file, box.data, "boards")
        check_style(report, "board-style", board, style["board"], at, "board")
        if box.name is not None:
            report.check("box-not-board", flat(board) != flat(box.name), at,
                         f"box {box.name} is named like its board {board}")


def box_field_problems(box):
    """What is missing from a box, as a list of reasons."""
    problems = []
    for name in ["box", "connectors"]:
        if name not in box.data:
            problems.append(f"no {name}")
    if has_board_pins(box) and "boards" not in box.data:
        problems.append("no boards, but a pin has an at")
    return problems


def has_board_pins(box):
    """Whether a pin of the box lands on a board (an `at` that is not `pass`)."""
    for pin in box.pins():
        if pin.at is not None and pin.at != "pass":
            return True
    return False


def file_name(box_name):
    """The file a box is written in: lower case, anything else than a letter
    or digit as `_`. `Pedal Box` -> `pedal_box.yaml`."""
    return re.sub(r"[^a-z0-9]", "_", str(box_name).lower()) + ".yaml"


def flat(name):
    """A name in lower case without separators, to compare names across styles:
    `PDU Box` -> `pdubox`."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# --- connectors ----------------------------------------------------------------

def check_connector(model, box, connector, report):
    """connector-style, connector-pins, pin-once."""
    style = model.settings.style["connector"]
    check_style(report, "connector-style", connector.name, style, connector.where, "connector")
    report.check("connector-pins", "pins" in connector.data, connector.where,
                 f"connector {connector.name} has no pins")
    check_pins_once(connector, report)


def check_pins_once(connector, report):
    """pin-once: every pin written once. Each pin after the first of its name
    is reported, where it is written."""
    seen = []
    for pin in connector.pins:
        if "pin" not in pin.data:
            continue   # pin-fields says so
        report.check("pin-once", pin.name not in seen, pin.where,
                     f"pin {pin.name} is written more than once in {connector.name}")
        seen.append(pin.name)


# --- pins ----------------------------------------------------------------------

def check_pin(model, box, pin, nets, report):
    what = f"pin {pin.name}"
    has_fields = "pin" in pin.data and "type" in pin.data
    report.check("pin-fields", has_fields, pin.where, f"{what} needs pin and type")
    if "pin" in pin.data:
        report.check("pin-string", isinstance(pin.name, str), pin.where, f"{what} is not a string")
    check_pin_order(pin, report)

    if pin.net is not None:
        nets.check_net(pin.net, pin.where)
    if pin.type is not None:
        nets.check_type(pin.net, pin.type, pin.where)
        check_pin_net(model, pin, report)
    else:
        report.skip("unfitted-note", pin.key)   # pin-fields says so

    if pin.to is not None:
        check_to(model, box, pin, report)
    if pin.at is not None:
        check_at(box, pin, report)


def check_to(model, box, pin, report):
    """to-known, to-not-own-box."""
    what = f"pin {pin.name}"
    # A box file that could not be read, or has no `box`, is a box nobody
    # knows the name of: a `to` pointing at it would repeat that one mistake.
    if model.all_boxes_named():
        report.check("to-known", model.is_box_or_device(pin.to), pin.where,
                     f"{what} goes to {pin.to}, which is no box or device")
    report.check("to-not-own-box", pin.to != box.name, pin.where, f"{what} goes to its own box")


def check_pin_order(pin, report):
    """pin-order: the fields in the order of STRUCT.md. Unknown fields are
    field-known's, so they are left out of the order."""
    written = [name for name in pin.data if name in PIN_FIELDS]
    in_order = [name for name in PIN_FIELDS if name in pin.data]
    report.check("pin-order", written == in_order, pin.where,
                 f"fields in the order {', '.join(written)}", pin.key)


def check_pin_net(model, pin, report):
    """pin-net, spare-no-to, and unfitted-note on an unfitted pin."""
    no_net = model.no_net_types()
    has_net = pin.net is not None
    if pin.type in no_net:
        report.check("pin-net", not has_net, pin.where, f"{pin.type} pin {pin.name} has net {pin.net}")
        report.check("spare-no-to", pin.to is None, pin.where,
                     f"{pin.type} pin {pin.name} goes to {pin.to}, but no wire leaves it")
    else:
        report.check("pin-net", has_net, pin.where, f"pin {pin.name} ({pin.type}) has no net")

    if pin.type == "unfitted":
        report.check("unfitted-note", "note" in pin.data, pin.where,
                     f"unfitted pin {pin.name} has no note on what it was for", pin.key)


def check_at(box, pin, report):
    """at-form, and at-pass on a `pass` pin."""
    if pin.at == "pass":
        report.check("at-pass", has_pin_to_pass_to(box, pin), pin.where,
                     f"{pin.net} {pin.type} passes through, but no other connector of {box.name} has it",
                     pin.key)
        return

    board, colon, board_pin = pin.at.partition(":")
    ok = colon != "" and board != "" and board_pin != ""
    # Without `boards`, box-fields already says so: only the form is checked here.
    if "boards" in box.data:
        ok = ok and box.has_board(board)
    report.check("at-form", ok, pin.where, f"pin {pin.name} at {pin.at} is not pass or <board>:<pin> on a board of {box.name}")


def has_pin_to_pass_to(box, pin):
    """Whether another connector of the box has a pin with the same net and type."""
    if pin.net is None:
        return False
    for other in box.pins():
        if other.connector != pin.connector and other.is_on(pin.net, pin.type):
            return True
    return False
