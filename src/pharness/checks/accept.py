"""Accepted entries, once every other check ran (CONFIG.md, Rule levels)."""


def check_accept(model, report):
    """accept-known and accept-used on every entry under `accept`."""
    # While a box file is unread or has no `box`, its pins are unknown and the
    # checks across boxes did not run: that one mistake is already reported.
    if not model.all_boxes_named():
        return
    entries = entries_by_rule(model)
    for rule, accepted in report.accepted.items():
        for entry, at in accepted.items():
            known = report.check("accept-known", entry in entries[rule], at,
                                 f"{rule}: there is no {entry}")
            if known:
                check_accept_used(rule, entry, at, report)


def check_accept_used(rule, entry, at, report):
    """accept-used: the entry still breaks its rule. Not judged when the rule
    is `off`, or was skipped on the entry because of another mistake."""
    if report.level(rule) == "off" or (rule, entry) in report.skipped:
        return
    report.check("accept-used", (rule, entry) in report.accept_hits, at,
                 f"{rule}: {entry} no longer breaks it, remove it")


def entries_by_rule(model):
    """Every entry each adjustable rule can be accepted on, named as `accept`
    names it (CONFIG.md, Rule levels)."""
    pins = [pin.key for pin in model.pins()]
    conductors = [f"{net} {type_}" for net, type_ in model.conductors()]
    outs = [node.key for node in model.nodes()]
    buses = list(model.car.buses)
    links = list(model.car.links)
    devices = list(model.car.devices)
    cables = [cable.name for cable in model.cables]
    return {
        "to-reaches": pins,
        "at-pass": pins,
        "unfitted-note": pins,
        "pin-order": pins,
        "conductor-one-end": conductors,
        "bus-reach": conductors + wire_conductors(model),
        "chain-out-used": outs,
        "chain-order": outs,
        "ends-match": buses + links,
        "bus-internal": buses,
        "device-used": devices,
        "to-cabled": pins,
        "pair-cable": pins,
        "cable-used": cables,
        "hv-orange": list(model.settings.colors) + pins,
    }


def wire_conductors(model):
    """The conductors only on listed wires, named like conductors."""
    return [f"{wire.net} {wire.type}" for cable in model.cables for wire in cable.wires]
