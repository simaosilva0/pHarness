"""cables/<cable>.yaml, and the `cable` of every connector and pin (STRUCT.md,
cables; CONFIG.md, Boxes, connectors, devices, boards, cables)."""

from ..project.fields import where
from .boxes import file_name
from .names import check_style

WIRE_NEEDS = ["net", "type", "from", "to"]


def check_cables(model, nets, report):
    for cable in model.cables:
        check_cable(model, cable, report)
        for wire in cable.wires:
            check_wire(model, cable, wire, nets, report)

    # These look across every box. While a box file is unread or has no `box`,
    # its connectors are unknown, and every end in it would look wrong: that
    # one mistake is already reported.
    if not model.all_boxes_named():
        return
    references_ok = True
    for box in model.boxes:
        for connector in box.connectors:
            connector_ok = check_connector_cable(model, box, connector, report)
            references_ok = references_ok and connector_ok
            for pin in connector.pins:
                pin_ok = check_pin_cable(model, pin, connector_ok, report)
                references_ok = references_ok and pin_ok
    check_cables_used(model, references_ok, report)
    check_pair_cables(model, report)


# --- the cable -----------------------------------------------------------------

def check_cable(model, cable, report):
    """cable-fields, cable-style, cable-file, cable-ends."""
    missing = [name for name in ["cable", "ends"] if name not in cable.data]
    report.check("cable-fields", not missing, f"{cable.file}:{cable.data.line}",
                 f"cable: no {', '.join(missing)}")

    if cable.name is not None:
        at = where(cable.file, cable.data, "cable")
        check_style(report, "cable-style", cable.name, model.settings.style["cable"], at, "cable")
        expected = file_name(cable.name)
        report.check("cable-file", cable.path.name == expected, at,
                     f"cable {cable.name} is in {cable.path.name}, not {expected}")

    if "ends" in cable.data:
        check_cable_ends(model, cable, report)


def check_cable_ends(model, cable, report):
    """cable-ends: at least two ends, each once, each a connector or a device."""
    at = where(cable.file, cable.data, "ends")
    ends = cable.ends
    report.check("cable-ends", len(ends) >= 2, at, f"cable {cable.name} has {len(ends)} end(s), not two or more")

    seen = []
    for end in ends:
        report.check("cable-ends", end not in seen, at, f"cable {cable.name}: {end} is written twice")
        seen.append(end)

    # A box nobody knows the name of would make its connectors look unknown.
    if not model.all_boxes_named():
        return
    for end in ends:
        known = model.is_device(end) or model.connector(end) is not None
        report.check("cable-ends", known, at,
                     f"cable {cable.name}: {end} is no device or <box>.<connector>")


def check_wire(model, cable, wire, nets, report):
    """wire-fields on a listed wire, and its net and type like any other."""
    missing = [name for name in WIRE_NEEDS if name not in wire.data]
    report.check("wire-fields", not missing, wire.where, f"wire: no {', '.join(missing)}")

    for end in wire.ends:
        if end is None:
            continue   # missing, said above
        is_device_end = model.is_device(end) and end in cable.ends
        report.check("wire-fields", is_device_end, wire.where,
                     f"wire end {end} is no device end of {cable.name}")
    from_, to = wire.ends
    if from_ is not None:
        report.check("wire-fields", from_ != to, wire.where, f"wire goes from {from_} to itself")

    if wire.net is not None:
        nets.check_net(wire.net, wire.where)
    if wire.type is not None:
        nets.check_type(wire.net, wire.type, wire.where)


# --- connectors and pins ---------------------------------------------------------

def check_connector_cable(model, box, connector, report):
    """cable-known and cable-on-end on the `cable` of a connector, once for all
    its pins. Returns False when one broke, so its pins are not judged again."""
    name = connector.data.get("cable")
    if name is None:
        return True
    cable = check_cable_known(model, name, connector.where, report)
    if cable is None:
        return False
    if not model.cable_ends_known(cable):
        return True   # cable-ends says so; the pins skip this cable too
    end = f"{box.name}.{connector.name}"
    return report.check("cable-on-end", end in cable.ends, connector.where,
                        f"connector {connector.name} is on {name}, which does not end at {end}")


def check_pin_cable(model, pin, connector_ok, report):
    """cable-to, cable-known, cable-on-end, cable-far-pin, to-cabled on one pin.
    Returns False when its `cable` names no cable, or a cable it is not on."""
    if pin.type in model.no_net_types():
        return True   # no wire leaves it: spare-no-to says if one is written
    own = "cable" in pin.data

    if own and not report.check("cable-to", pin.to is not None, pin.where,
                                f"pin {pin.name} is on {pin.cable}, but has no to"):
        return False

    if pin.cable is None:
        if model.has_cables and pin.to is not None:
            report.check("to-cabled", False, pin.where, f"the wire to {pin.to} is on no cable", pin.key)
        return True
    if model.has_cables:
        report.check("to-cabled", True, pin.where, "", pin.key)

    if own:
        cable = check_cable_known(model, pin.cable, pin.where, report)
        if cable is None:
            return False
    elif not connector_ok:
        return True   # its connector's cable is wrong, and was reported there
    else:
        cable = model.cable(pin.cable)
    if not model.cable_ends_known(cable):
        return True   # cable-ends says so

    end = f"{pin.box}.{pin.connector}"
    if own and not report.check("cable-on-end", end in cable.ends, pin.where,
                                f"pin {pin.name} is on {cable.name}, which does not end at {end}"):
        return False
    if not model.is_box_or_device(pin.to):
        return True   # to-known says so
    if not check_to_on_cable(model, pin, cable, report):
        return False
    if model.is_box(pin.to):
        check_far_pin(model, pin, cable, report)
    return True


def check_cable_known(model, name, at, report):
    """cable-known: the cable exists. Returns it, or None. While a cable file is
    unread or has no `cable`, an unknown name may be that one: not judged."""
    cable = model.cable(name)
    if cable is None and model.all_cables_named():
        report.check("cable-known", False, at, f"there is no cable {name}")
    return cable


def check_to_on_cable(model, pin, cable, report):
    """cable-on-end: the pin's `to` is an end of its cable: the device, or a
    connector of that box. Returns whether it passed."""
    if model.is_device(pin.to):
        ok = pin.to in cable.ends
    else:
        ok = bool(model.ends_in_box(cable, pin.to))
    return report.check("cable-on-end", ok, pin.where,
                        f"pin {pin.name} goes to {pin.to}, but {cable.name} does not end there")


def check_far_pin(model, pin, cable, report):
    """cable-far-pin: a pin going to a box finds exactly one pin there with its
    net and type, on the same cable, on a connector end of that cable."""
    if pin.net is None or pin.type is None:
        return   # pin-fields or pin-net says so
    far = model.far_pins(pin, cable)
    if len(far) == 1:
        report.check("cable-far-pin", True, pin.where, "")
        return
    found = "no pin" if not far else ", ".join(other.key for other in far)
    report.check("cable-far-pin", False, pin.where,
                 f"{pin.net} {pin.type} on {cable.name} to {pin.to}: {found}, not exactly one")


# --- cables in use -----------------------------------------------------------------

def check_cables_used(model, references_ok, report):
    """cable-used: a pin or a listed wire is on every cable. While a `cable` on
    a connector or a pin is misspelled or on the wrong cable, an unused cable
    may be the one it meant: not judged."""
    on_pins = {pin.cable for pin in model.pins()}
    for cable in model.cables:
        if cable.name is None:
            continue   # cable-fields says so
        used = cable.name in on_pins or bool(cable.wires)
        if not used and not references_ok:
            report.skip("cable-used", cable.name)
            continue
        report.check("cable-used", used, where(cable.file, cable.data, "cable"),
                     f"no wire runs in {cable.name}", cable.name)


# --- twisted pairs -----------------------------------------------------------------

def check_pair_cables(model, report):
    """pair-cable: the two wires of a twisted pair going to the same place are
    on the same cable. Judged on the wire of the pair's first type, against
    the wires of the second leaving the same box for the same place. A wire
    that is not sound (on no cable, or not reaching its far end) is left to
    the cable rules, and so is a first wire with no partner."""
    if not model.has_cables:
        return
    for first, second in model.settings.twisted_pairs():
        for pin in model.pins():
            if pin.type != first or pin.to is None or pin.cable is None:
                continue
            if not is_sound(model, pin):
                report.skip("pair-cable", pin.key)   # the cable rules say so
                continue
            partners = [other for other in model.box(pin.box).pins()
                        if other.is_on(pin.net, second) and other.to == pin.to
                        and is_sound(model, other)]
            if not partners:
                continue
            cables = [other.cable for other in partners]
            report.check("pair-cable", pin.cable in cables, pin.where,
                         f"{pin.net} {first} to {pin.to} is on {pin.cable}, "
                         f"{second} on {', '.join(sorted(set(cables)))}", pin.key)
        for cable in model.cables:
            for wire in cable.wires:
                if wire.type != first:
                    continue
                partners = [other_cable.name for other_cable in model.cables
                            for other in other_cable.wires
                            if other.net == wire.net and other.type == second
                            and set(other.ends) == set(wire.ends)]
                if partners:
                    report.check("pair-cable", cable.name in partners, wire.where,
                                 f"{wire.net} {first} is on {cable.name}, "
                                 f"{second} on {', '.join(sorted(set(partners)))}")


def is_sound(model, pin):
    """Whether the wire leaving a pin runs in a known cable to its far end:
    the device, or exactly one pin in that box."""
    cable = model.cable(pin.cable)
    if cable is None or not model.cable_ends_known(cable):
        return False
    if model.is_device(pin.to):
        return pin.to in cable.ends
    return model.far_pin(pin) is not None
