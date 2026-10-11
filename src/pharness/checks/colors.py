"""Wire colors across the project (CONFIG.md, Colors; STRUCT.md, cables): the
types under `colors`, and the colors on pins and listed wires. The palette,
the mode and the colors' names under `colors` are checked with config.yaml."""

from ..project.colors import base_of, in_palette, is_hv
from ..project.labels import split_type
from .config import check_color_name


def check_colors(model, nets, report):
    settings = model.settings
    for type_, color in settings.colors.items():
        at = settings.colors_at[type_]
        check_color_type(model, nets, type_, at, report)
        if named_right(color, settings):
            check_hv_orange(type_, color, at, type_, report)

    for pin in model.pins():
        check_pin_color(model, pin, report)
    for cable in model.cables:
        for wire in cable.wires:
            check_listed_wire_color(model, wire, report)

    # Far pins are only known once every box is.
    if model.all_boxes_named():
        check_wire_colors(model, report)
    check_colors_complete(model, report)


def named_right(color, settings):
    """Whether a color can be judged: written in the palette. When not,
    color-name says so; when the palette is set wrong, palette-name does."""
    return settings.palette is not None and in_palette(color, settings.palette)


# --- under `colors` --------------------------------------------------------------

def check_color_type(model, nets, type_, at, report):
    """color-type: a type a pin may have, and one with a colored wire: not a
    shield, spare or unfitted."""
    word, qualifier = split_type(type_)
    if nets.is_word_of("shield", word) or nets.is_word_of("no_net", word):
        report.check("color-type", False, at, f"{type_} has no colored wire")
        return
    if nets.is_word_of("chain", word):
        outs = [node.out for node in model.nodes()]
        ok = qualifier in outs
    else:
        ok = nets.fits_a_kind(word, qualifier)
    report.check("color-type", ok, at, f"{type_} is not a type of any kind")


def check_hv_orange(type_, color, at, entry, report):
    """hv-orange: an hv wire is orange, and no other wire is. Orange is the
    base: `orange/black` is orange, `black/orange` is not."""
    orange = base_of(color) == "orange"
    if is_hv(type_):
        report.check("hv-orange", orange, at, f"{type_} is high voltage, so orange, not {color}", entry)
    else:
        report.check("hv-orange", not orange, at, f"{type_} is not high voltage, so not {color}", entry)


# --- on pins and listed wires -----------------------------------------------------

def check_pin_color(model, pin, report):
    """color-name and hv-orange on a pin's own color."""
    color = pin.data.get("color")
    if color is None or pin.type is None or pin.type in model.no_net_types():
        return   # spare-no-to says so on a spare pin
    settings = model.settings
    if settings.palette is None:
        return
    if check_color_name(color, settings.palette, pin.where, f"pin {pin.name}: ", report):
        check_hv_orange(pin.type, color, pin.where, pin.key, report)


def check_listed_wire_color(model, wire, report):
    """color-name and hv-orange on a listed wire's own color. A listed wire has
    no name `accept` could use."""
    color = wire.data.get("color")
    settings = model.settings
    if color is None or wire.type is None or settings.palette is None:
        return
    if check_color_name(color, settings.palette, wire.where, "wire: ", report):
        check_hv_orange(wire.type, color, wire.where, None, report)


def check_wire_colors(model, report):
    """wire-color: the two pins of a wire do not give it two colors. Reported
    once, on the first of the two."""
    reported = set()
    for pin in model.pins():
        far = model.far_pin(pin)
        if far is None or far.key in reported:
            continue
        mine, theirs = pin.data.get("color"), far.data.get("color")
        if mine is None or theirs is None:
            continue
        ok = report.check("wire-color", mine == theirs, pin.where,
                          f"the wire to {far.key} is {mine} here and {theirs} there")
        if not ok:
            reported.add(pin.key)


# --- every type with a color --------------------------------------------------------

def check_colors_complete(model, report):
    """colors-complete: under `strict`, every type on a wire has a color under
    `colors`, but hv and chains, whose color is set (orange, and one color per
    chain). Reported on `colors`, once per type."""
    settings = model.settings
    if settings.color != "strict":
        return
    chains = settings.kinds.get("chain")
    chain_words = chains.words if chains is not None else []
    for type_ in types_on_wires(model):
        word, _ = split_type(type_)
        if is_hv(type_) or word in chain_words:
            continue
        report.check("colors-complete", type_ in settings.colors, settings.colors_where,
                     f"no color for {type_}")


def types_on_wires(model):
    """Every type a wire has, in reading order, each once: the types of pins on
    a cable and of listed wires. Shields have no colored wire."""
    types = []
    for pin in model.pins():
        if pin.cable is not None and pin.type is not None:
            types.append(pin.type)
    for cable in model.cables:
        for wire in cable.wires:
            if wire.type is not None:
                types.append(wire.type)

    shields = model.settings.kinds.get("shield")
    shield_words = shields.words if shields is not None else []
    seen = []
    for type_ in types:
        word, _ = split_type(type_)
        if type_ not in seen and word not in shield_words:
            seen.append(type_)
    return seen
