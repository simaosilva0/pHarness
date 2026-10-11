"""Conductors and routes: what the pins add up to across boxes (CONFIG.md: the
start, Labels, Chains; STRUCT.md: car.yaml, boxes)."""

from ..project.labels import split_type, wire_label


def check_routes(model, nets, report):
    check_labels(model, report)
    # These look across every box. While a box file is unread or has no `box`,
    # its pins are unknown, and every route through it would look broken: that
    # one mistake is already reported.
    if not model.all_boxes_named():
        return
    check_conductors(model, nets, report)
    check_tos(model, report)
    check_ends(model, report)
    check_devices_used(model, report)
    check_chain_outs(model, report)


# --- conductors ----------------------------------------------------------------

def check_conductors(model, nets, report):
    """conductor-one-end: a conductor has two pins, or one pin going to a device.
    A screen is usually tied down at one end only, so shields are left out."""
    for (net, type_), pins in model.conductors().items():
        word, _ = split_type(type_)
        if nets.is_word_of("shield", word):
            continue
        first = pins[0]
        ok = len(pins) > 1 or model.is_device(first.to)
        report.check("conductor-one-end", ok, first.where,
                     f"{net} {type_} is on one pin, not going to a device", f"{net} {type_}")


def check_labels(model, report):
    """label-unique: no two conductors get the same wire label. Reported on the
    first pin of the first conductor."""
    labels = {}   # label -> [(net, type, first pin)]
    for (net, type_), pins in model.conductors().items():
        label = wire_label(model.settings, net, type_)
        if label is None:
            continue   # a type that fits no kind: pin-type says so
        labels.setdefault(label, []).append((net, type_, pins[0]))

    for label, same in labels.items():
        names = ", ".join(f"{net} {type_}" for net, type_, _ in same)
        report.check("label-unique", len(same) == 1, same[0][2].where, f"{label} is the label of {names}")


# --- where the wires go ----------------------------------------------------------

def check_tos(model, report):
    """to-reaches: a pin going to a box finds a pin with its net and type there."""
    for pin in model.pins():
        if pin.to is None or model.is_device(pin.to):
            continue
        far = model.box(pin.to)
        if far is None or pin.net is None or pin.type is None:
            report.skip("to-reaches", pin.key)   # to-known, pin-fields or pin-net says so
            continue
        reaches = any(other.is_on(pin.net, pin.type) for other in far.pins())
        report.check("to-reaches", reaches, pin.where,
                     f"{pin.net} {pin.type} goes to {pin.to}, which has no such pin", pin.key)


# --- buses and links ---------------------------------------------------------------

def check_ends(model, report):
    """ends-known, bus-internal on buses, then ends-match. Each runs only when
    the one before passed: a misspelled end, or a missing `internal: true`,
    would otherwise also make the ends look wrong."""
    car = model.car
    for group, entries in [("buses", car.buses), ("links", car.links)]:
        lines = car.data.get(group).at
        for name, entry in entries.items():
            if not check_bus_or_link_ends(model, group, name, entry, lines[name], report):
                report.skip("bus-internal", name)
                report.skip("ends-match", name)


def check_bus_or_link_ends(model, group, name, entry, line, report):
    """The ends of one bus or link. Returns False when the ends could not be
    judged because of another mistake."""
    if "ends" not in entry:
        return False   # bus-fields says so
    at = f"car.yaml:{line}"
    ends = entry["ends"]
    if not check_ends_known(model, name, ends, at, report):
        return False
    if group == "buses" and not check_bus_internal(model, name, entry, ends, at, report):
        report.skip("ends-match", name)
        return True
    if not entry.get("internal"):
        check_ends_match(model, name, ends, at, report)
    return True


def check_ends_known(model, name, ends, at, report):
    """ends-known. Returns whether every end is known, so the checks that
    compare ends do not repeat a misspelled one."""
    all_known = True
    for end in ends:
        if not report.check("ends-known", model.is_box_or_device(end), at,
                            f"{name} end {end} is no box or device"):
            all_known = False
    return all_known


def check_ends_match(model, name, ends, at, report):
    """ends-match: the ends are the boxes the bus or link lands in (a pin on it
    that is not `pass`) and the devices a pin on it goes to."""
    on = lands_on(model, name)
    missing = [end for end in on if end not in ends]
    extra = [end for end in ends if end not in on]

    reasons = []
    if missing:
        reasons.append(f"on it but not in ends: {', '.join(missing)}")
    if extra:
        reasons.append(f"in ends but it does not land there: {', '.join(str(end) for end in extra)}")
    report.check("ends-match", not reasons, at, "; ".join(reasons), name)


def lands_on(model, net):
    """The boxes a net lands in and the devices it goes to, in reading order."""
    on = []
    for pin in model.pins():
        if pin.net != net:
            continue
        if pin.at != "pass" and pin.box not in on:
            on.append(pin.box)
        if model.is_device(pin.to) and pin.to not in on:
            on.append(pin.to)
    return on


def check_bus_internal(model, name, bus, ends, at, report):
    """bus-internal: `internal` exactly when the bus has one end, a box.
    Returns whether it passed."""
    internal = bus.get("internal", False)
    alone_in_a_box = len(ends) == 1 and model.is_box(ends[0])
    ends_text = ", ".join(str(end) for end in ends)
    return report.check("bus-internal", internal == alone_in_a_box, at,
                 f"internal: {str(internal).lower()}, with ends: {ends_text}", name)


# --- devices -------------------------------------------------------------------------

def check_devices_used(model, report):
    """device-used: every device is a `to`, an end, or a chain node."""
    used = devices_used(model)
    devices = model.car.data.get("devices")
    for name in model.car.devices:
        report.check("device-used", name in used, f"car.yaml:{devices.at[name]}",
                     "no pin, bus, link or chain uses it", name)


def devices_used(model):
    used = []
    for pin in model.pins():
        used.append(pin.to)
    for entry in list(model.car.buses.values()) + list(model.car.links.values()):
        used.extend(entry.get("ends", []))
    for node in model.nodes():
        if node.box is None:
            used.append(node.name)
    return used


# --- chains --------------------------------------------------------------------------

def check_chain_outs(model, report):
    """chain-out-used: every out is on a pin, unless its node and the next node
    are in the same box. Whether the loop runs from node to node waits for
    cables (step 9)."""
    for chain, nodes in model.car.chains.items():
        for i, node in enumerate(nodes):
            if "out" not in node.data:
                continue   # chain-fields says so
            following = nodes[i + 1] if i + 1 < len(nodes) else None
            if not boxes_known(model, node, following):
                report.skip("chain-out-used", node.key)   # chain-node says so
                continue
            if following is not None and node.box is not None and node.box == following.box:
                continue
            on_a_pin = any(pin.is_on(chain, node.type) for pin in model.pins())
            report.check("chain-out-used", on_a_pin, node.where,
                         f"leaves {node.name}, but is on no pin", node.key)


def boxes_known(model, node, following):
    """Whether the boxes the node and the one after it are in exist."""
    for one in [node, following]:
        if one is not None and one.box is not None and not model.is_box(one.box):
            return False
    return True
