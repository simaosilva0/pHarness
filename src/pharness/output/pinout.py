"""The pinout tables: every box, every connector, every pin, as plain rows.

Nothing here knows about HTML. The page is drawn from these rows (page.py),
and later outputs can read them too.
"""

from dataclasses import dataclass, field

from ..project.labels import wire_label


@dataclass
class Row:
    """One pin, as its table shows it."""

    pin: str
    net: str | None
    type: str | None
    wire: str | None    # the wire label, built by the tool
    to: str | None
    to_is_box: bool     # whether `to` is a box of the project, so it can link there
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
class Pinout:
    car: str
    boxes: list      # [BoxPinout], in reading order
    warnings: list   # every warning of the report, in file and line order

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
    boxes = [box_pinout(model, box, warnings) for box in model.boxes]
    return Pinout(model.car.data.get("car"), boxes, warnings)


def box_pinout(model, box, warnings):
    connectors = []
    for connector in box.connectors:
        rows = [pin_row(model, pin, warnings) for pin in connector.pins]
        part = connector.data.get("part")
        note = connector.data.get("note")
        connectors.append(ConnectorTable(connector.name, part, note, rows))
    return BoxPinout(box.name, box.file, box.boards, box.data.get("note"), connectors)


def pin_row(model, pin, warnings):
    unused = pin.type in model.no_net_types()
    wire = None
    if not unused and pin.net is not None:
        wire = wire_label(model.settings, pin.net, pin.type)

    return Row(
        pin=str(pin.name),
        net=pin.net,
        type=pin.type,
        wire=wire,
        to=pin.to,
        to_is_box=model.is_box(pin.to),
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
