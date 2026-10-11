"""The parts of a project, once read: boxes, connectors, pins, cables, and what
car.yaml declares. The checks work on these, never on raw YAML."""

from dataclasses import dataclass, field

from .load import Map


@dataclass
class Pin:
    box: str          # the box's name
    connector: str
    data: Map         # its fields: pin, net, type, to, cable, color, at, note
    where: str        # file:line
    connector_cable: str | None = None   # the `cable` of its connector

    @property
    def name(self):
        return self.data.get("pin")

    @property
    def net(self):
        return self.data.get("net")

    @property
    def type(self):
        return self.data.get("type")

    @property
    def to(self):
        return self.data.get("to")

    @property
    def cable(self):
        """The cable the wire leaving this pin runs in: its own `cable`, or its
        connector's when a wire leaves it (it has a `to`)."""
        if "cable" in self.data:
            return self.data["cable"]
        if self.to is not None:
            return self.connector_cable
        return None

    @property
    def at(self):
        return self.data.get("at")

    @property
    def key(self):
        """The pin as `accept` names it: <box>.<connector>.<pin>."""
        return f"{self.box}.{self.connector}.{self.name}"

    def is_on(self, net, type_):
        return self.net == net and self.type == type_


@dataclass
class Connector:
    name: str
    data: Map
    where: str
    pins: list = field(default_factory=list)


@dataclass
class Box:
    name: str         # the `box` field; may be missing or wrong, the checks say so
    file: str         # the file's path from the project
    path: object      # the file as a Path
    data: Map
    boards: list
    connectors: list = field(default_factory=list)

    def pins(self):
        for connector in self.connectors:
            yield from connector.pins

    def has_board(self, board):
        return board in self.boards


@dataclass
class Wire:
    """A wire listed in a cable: from one device straight to another."""

    cable: str
    data: Map         # its fields: net, type, from, to, color
    where: str

    @property
    def net(self):
        return self.data.get("net")

    @property
    def type(self):
        return self.data.get("type")

    @property
    def ends(self):
        return [self.data.get("from"), self.data.get("to")]


@dataclass
class Cable:
    name: str         # the `cable` field; may be missing or wrong, the checks say so
    file: str         # the file's path from the project
    path: object      # the file as a Path
    data: Map
    ends: list
    wires: list = field(default_factory=list)   # [Wire]


@dataclass
class Node:
    """One node of a chain."""

    chain: str
    data: Map
    where: str

    @property
    def name(self):
        return self.data.get("node")

    @property
    def out(self):
        """The out label as text: `out: 1` and `out: '1'` are the same."""
        return str(self.data.get("out"))

    @property
    def box(self):
        return self.data.get("box")

    @property
    def type(self):
        """The type of a pin on the conductor leaving this node."""
        return f"chain:{self.out}"

    @property
    def key(self):
        """The out as `accept` names it: <chain> chain:<out>."""
        return f"{self.chain} {self.type}"


@dataclass
class Car:
    """What car.yaml declares, each entry a Map with its lines."""

    data: Map
    devices: dict   # name -> Map
    buses: dict     # name -> Map
    links: dict     # name -> Map
    chains: dict    # name -> [Node]


@dataclass
class Model:
    """The whole project, read: the settings, the car and its boxes."""

    settings: object   # settings.Settings
    car: Car
    boxes: list        # [Box]
    unread: list       # box files that could not be read: their boxes are unknown
    cables: list = field(default_factory=list)          # [Cable]
    unread_cables: list = field(default_factory=list)   # cable files that could not be read
    has_cables: bool = False                            # whether there is a cables/ folder

    def box(self, name):
        """The box with this name, or None."""
        if not isinstance(name, str):
            return None
        for box in self.boxes:
            if box.name == name:
                return box
        return None

    def all_boxes_named(self):
        """Whether every box file was read and names its box. When one is not,
        a box is missing from box_names()."""
        if self.unread:
            return False
        return all(isinstance(box.name, str) for box in self.boxes)

    def box_names(self):
        return {box.name for box in self.boxes if isinstance(box.name, str)}

    def cable(self, name):
        """The cable with this name, or None."""
        if not isinstance(name, str):
            return None
        for cable in self.cables:
            if cable.name == name:
                return cable
        return None

    def all_cables_named(self):
        """Whether every cable file was read and names its cable, like
        all_boxes_named()."""
        if self.unread_cables:
            return False
        return all(isinstance(cable.name, str) for cable in self.cables)

    def cable_ends_known(self, cable):
        """Whether the cable has `ends`, as a list, and every end is a device or
        a connector. When not, its pins cannot be judged against its ends."""
        if not isinstance(cable.data.get("ends"), list):
            return False
        return all(self.is_device(end) or self.connector(end) is not None for end in cable.ends)

    def ends_in_box(self, cable, box_name):
        """The connectors of a box that are ends of the cable, by name."""
        connectors = []
        for end in cable.ends:
            found = self.connector(end)
            if found is not None and found[0].name == box_name:
                connectors.append(found[1].name)
        return connectors

    def far_pins(self, pin, cable):
        """The pins a wire from `pin`, going to a box, could end on: in that box,
        on a connector end of the cable, with the pin's net and type, on the
        same cable. A right wire has exactly one."""
        connectors = self.ends_in_box(cable, pin.to)
        return [other for other in self.box(pin.to).pins()
                if other.connector in connectors and other.is_on(pin.net, pin.type)
                and other.cable == cable.name]

    def far_pin(self, pin):
        """The one pin the wire from `pin` ends on in another box, or None: it
        goes to a device, is on no cable, or the cable does not say which."""
        if pin.to is None or not self.is_box(pin.to) or pin.net is None or pin.type is None:
            return None
        cable = self.cable(pin.cable)
        if cable is None or not self.cable_ends_known(cable):
            return None
        far = self.far_pins(pin, cable)
        if len(far) != 1:
            return None
        return far[0]

    def connector(self, end):
        """The connector a cable end `<box>.<connector>` names, as (Box,
        Connector), or None. Matched whole, so a dot in a name is no problem."""
        if not isinstance(end, str):
            return None
        for box in self.boxes:
            for connector in box.connectors:
                if end == f"{box.name}.{connector.name}":
                    return box, connector
        return None

    def pins(self):
        for box in self.boxes:
            yield from box.pins()

    def conductors(self):
        """Every conductor: (net, type) -> the pins on it. Pins with the same
        net and type are one conductor (CONFIG.md, the start). Spare and
        unfitted pins carry no conductor, even with a net written on them."""
        conductors = {}
        for pin in self.pins():
            if pin.net is None or pin.type is None:
                continue
            if pin.type in self.no_net_types():
                continue
            conductors.setdefault((pin.net, pin.type), []).append(pin)
        return conductors

    def no_net_types(self):
        """The types that never have a net: the words of the `no_net` kind."""
        kind = self.settings.kinds.get("no_net")
        if kind is None:
            return []
        return kind.words

    def nodes(self):
        for nodes in self.car.chains.values():
            yield from nodes

    def chain_outs(self, chain):
        return [node.out for node in self.car.chains.get(chain, [])]

    def is_box(self, name):
        return isinstance(name, str) and name in self.box_names()

    def is_device(self, name):
        return isinstance(name, str) and name in self.car.devices

    def is_box_or_device(self, name):
        return self.is_box(name) or self.is_device(name)
