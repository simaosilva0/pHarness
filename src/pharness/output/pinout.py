"""The pinout tables: every box, every connector, every pin, every cable and
its wires, as plain rows.

Nothing here knows about HTML. The page is drawn from these rows (page.py),
and later outputs can read them too.
"""

from dataclasses import dataclass, field

from ..project.chains import chain_taps
from ..project.colors import Colors
from ..project.labels import split_type, wire_label
from .diagram import build_diagram


@dataclass
class Row:
    """One pin, as its table shows it."""

    pin: str
    net: str | None
    type: str | None
    wire: str | None    # the wire label, built by the tool
    to: str | None
    to_is_box: bool     # whether `to` is a box of the project, so it can link there
    far: str | None     # the pin the wire ends on, <box>.<connector>.<pin>, once a cable says
    far_where: str | None   # that pin's file:line, to link to its row
    cable: str | None
    color: str | None   # the color of the wire leaving the pin
    color_picked: bool  # picked by the tool, not written by the project
    at: str | None
    note: str | None
    unused: bool        # spare or unfitted: no conductor on it
    where: str          # file:line, as the report names it
    warnings: list = field(default_factory=list)   # the warnings on this pin


@dataclass
class ConnectorTable:
    name: str
    part: str | None
    note: str | None
    rows: list


@dataclass
class BoxPinout:
    name: str
    file: str
    boards: list
    note: str | None
    connectors: list

    def pin_count(self):
        count = 0
        for connector in self.connectors:
            count += len(connector.rows)
        return count


@dataclass
class WireRow:
    """One wire of a cable: from a pin to a pin or a device, or between devices."""

    start: str          # <box>.<connector>.<pin>, or a device
    start_where: str | None   # the pin's file:line, to link to its row
    end: str
    end_where: str | None
    wire: str | None    # the wire label
    type: str
    color: str | None
    color_picked: bool
    tap: bool = False   # a chain wire that only taps the chain


@dataclass
class CableTable:
    name: str
    file: str
    ends: list
    part: str | None
    note: str | None
    wires: list         # [WireRow], in reading order


@dataclass
class ColorRow:
    """One type and the color of its wires, for the legend."""

    type: str
    color: str
    picked: bool
    tap: bool = False   # the color of the wires that only tap a chain


@dataclass
class Pinout:
    car: str
    boxes: list      # [BoxPinout], in reading order
    warnings: list   # every warning of the report, in file and line order
    cables: list = field(default_factory=list)   # [CableTable], in reading order
    colors: list = field(default_factory=list)   # [ColorRow], every type on a wire
    diagram: object = None                       # diagram.Diagram, the car as nodes and links

    def wire_count(self):
        return sum(len(cable.wires) for cable in self.cables)

    def connector_count(self):
        count = 0
        for box in self.boxes:
            count += len(box.connectors)
        return count

    def pin_count(self):
        count = 0
        for box in self.boxes:
            count += box.pin_count()
        return count


def build_pinout(model, report):
    """The pinout of a checked project. Call it only when the report has no
    errors: the rows trust that every name and type is right."""
    warnings = [p for p in report.sorted_problems() if p.level == "warn"]
    colors = Colors(model.settings)
    taps = chain_taps(model)
    boxes = [box_pinout(model, colors, taps, box, warnings) for box in model.boxes]
    cables = [cable_table(model, colors, taps, cable) for cable in model.cables]
    legend = color_legend(colors, cables)
    diagram = build_diagram(model, cables)
    return Pinout(model.car.data.get("car"), boxes, warnings, cables, legend, diagram)


def box_pinout(model, colors, taps, box, warnings):
    connectors = []
    for connector in box.connectors:
        rows = [pin_row(model, colors, taps, pin, warnings) for pin in connector.pins]
        part = connector.data.get("part")
        note = connector.data.get("note")
        connectors.append(ConnectorTable(connector.name, part, note, rows))
    return BoxPinout(box.name, box.file, box.boards, box.data.get("note"), connectors)


def pin_row(model, colors, taps, pin, warnings):
    unused = pin.type in model.no_net_types()
    wire = None
    if not unused and pin.net is not None:
        wire = wire_label(model.settings, pin.net, pin.type)
    far = model.far_pin(pin)
    color, picked = None, False
    if pin.to is not None and not unused:
        color, picked = wire_color(colors, pin, far, is_tap(taps, pin.net, pin.type, pin.box, pin.to))

    return Row(
        pin=str(pin.name),
        net=pin.net,
        type=pin.type,
        wire=wire,
        to=pin.to,
        to_is_box=model.is_box(pin.to),
        far=far.key if far is not None else None,
        far_where=far.where if far is not None else None,
        cable=pin.cable,
        color=color,
        color_picked=picked,
        at=pin.at,
        note=pin.data.get("note"),
        unused=unused,
        where=pin.where,
        warnings=warnings_on(pin, warnings),
    )


def warnings_on(pin, warnings):
    """The warnings reported on this pin's line. Pins are one per line, so the
    line is the pin."""
    return [warning for warning in warnings if warning.where == pin.where]


def wire_color(colors, pin, far, tap):
    """The color of the wire leaving a pin, and whether the tool picked it: the
    color written on either end, else its type's."""
    own = pin.data.get("color")
    if own is None and far is not None:
        own = far.data.get("color")
    if own is not None:
        return own, False
    return colors.of_type(pin.type, tap), colors.is_picked(pin.type)


def is_tap(taps, net, type_, one, other):
    """Whether the wire joining two places only taps its chain."""
    return frozenset([one, other]) in taps.get((net, type_), set())


# --- cables ------------------------------------------------------------------------

def cable_table(model, colors, taps, cable):
    """Every wire of a cable: from each pin on it to its device or far pin (a
    wire between two pins once), then the wires it lists."""
    wires = []
    done = set()   # pins whose wire is already a row
    for pin in model.pins():
        if pin.cable != cable.name or pin.to is None or pin.key in done:
            continue
        far = model.far_pin(pin)
        if model.is_box(pin.to) and far is None:
            continue   # its far pin is not known: no wire to show
        tap = is_tap(taps, pin.net, pin.type, pin.box, pin.to)
        color, picked = wire_color(colors, pin, far, tap)
        if far is not None:
            done.add(far.key)
            end, end_where = far.key, far.where
        else:
            end, end_where = pin.to, None
        wires.append(WireRow(pin.key, pin.where, end, end_where,
                             wire_label(model.settings, pin.net, pin.type), pin.type,
                             color, picked, tap))

    for wire in cable.wires:
        from_, to = wire.ends
        own = wire.data.get("color")
        tap = is_tap(taps, wire.net, wire.type, from_, to)
        color = colors.of_wire(own, wire.type, tap)
        picked = own is None and colors.is_picked(wire.type)
        wires.append(WireRow(from_, None, to, None, wire_label(model.settings, wire.net, wire.type),
                             wire.type, color, picked, tap))

    return CableTable(cable.name, cable.file, cable.ends, cable.data.get("part"),
                      cable.data.get("note"), wires)


def color_legend(colors, cables):
    """Every type on a wire with its type's color, sorted. A chain is one row,
    since all its outs share a color unless the project chose otherwise, and
    one more for its taps when it has any. A wire's own color is on its row,
    not here."""
    rows = []
    seen = set()
    for cable in cables:
        for wire in cable.wires:
            type_ = wire.type
            color = colors.of_type(type_, wire.tap)
            tap = wire.tap and color != colors.of_type(type_)   # a chosen color is the same on taps
            word, _ = split_type(type_)
            if colors.is_word_of("chain", word) and colors.is_picked(type_):
                type_ = f"{word}:*"
            if (type_, tap) in seen or color is None:
                continue
            seen.add((type_, tap))
            rows.append(ColorRow(type_, color, colors.is_picked(wire.type), tap))
    return sorted(rows, key=lambda row: (legend_order(row.type), row.tap))


def legend_order(type_):
    """By type word, then qualifier: ground, power:12v, power:5v..."""
    word, qualifier = split_type(type_)
    return (word, qualifier or "")
