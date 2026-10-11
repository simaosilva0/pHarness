"""The parts of a project, once read: boxes, connectors, pins, and what car.yaml
declares. The checks work on these, never on raw YAML."""

from dataclasses import dataclass, field

from .load import Map


@dataclass
class Pin:
    box: str          # the box's name
    connector: str
    data: Map         # its fields: pin, net, type, to, at, note
    where: str        # file:line

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
