"""The car as a diagram: a node for every box and device, a link for every pair
of nodes a cable joins, and where each node sits by default.

Nothing here knows about HTML or drawing. page.py hands this to the script that
draws it. Positions are in grid cells.
"""

import math
from dataclasses import dataclass, field

GRID = 20            # pixels in a cell, at zoom 1
BOX_SIZE = (12, 6)   # cells: boxes are bigger than devices
DEVICE_SIZE = (8, 2)
GAP = 2              # cells between devices
SIDE_GAP = 6         # cells between a box and its column of devices
BLOCK_GAP = 10       # cells between blocks, room for cables to pass on lines of their own


@dataclass
class Node:
    name: str
    kind: str           # "box" or "device"
    info: str           # a line under a box's name
    owner: str | None = None   # a device: the box whose column it sits in
    cables: int = 0     # cables that end on it, so its sides have a cell for each
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


@dataclass
class CableOnLink:
    name: str
    wires: int


@dataclass
class Link:
    """What joins two nodes: every cable that has an end on each."""

    a: str
    b: str
    cables: list = field(default_factory=list)   # [CableOnLink]

    @property
    def wires(self):
        return sum(cable.wires for cable in self.cables)


@dataclass
class Group:
    """A bus, a link or a chain and the nodes it touches."""

    name: str
    kind: str           # "bus", "link" or "chain"
    members: list       # node names, in reading order


@dataclass
class Diagram:
    nodes: list         # [Node]
    links: list         # [Link]
    groups: list = field(default_factory=list)   # [Group]

    def as_data(self):
        """The diagram as plain data, for the script that draws it."""
        return {
            "grid": GRID,
            "nodes": [dict(vars(node)) for node in self.nodes],
            "links": [{"a": link.a, "b": link.b, "wires": link.wires,
                       "cables": [dict(vars(cable)) for cable in link.cables]}
                      for link in self.links],
            "groups": [dict(vars(group)) for group in self.groups],
        }


def build_diagram(model, cables):
    """The diagram of a checked project. `cables` are the cable tables, which
    know how many wires each cable has."""
    nodes = []
    for box in model.boxes:
        pins = sum(len(connector.pins) for connector in box.connectors)
        info = f"{len(box.connectors)} connectors · {pins} pins"
        nodes.append(Node(box.name, "box", info))
    for name in model.car.devices:
        nodes.append(Node(name, "device", ""))

    wires = {table.name: len(table.wires) for table in cables}
    links = {}
    for cable in model.cables:
        ends = []
        for end in cable.ends:
            node = end_node(model, end)
            if node is not None and node not in ends:
                ends.append(node)
        # a cable is a star from its first end to the others; an end in the
        # same box as the first is no link
        for other in ends[1:]:
            key = tuple(sorted((ends[0], other)))
            link = links.setdefault(key, Link(*key))
            link.cables.append(CableOnLink(cable.name, wires.get(cable.name, 0)))

    diagram = Diagram(nodes, list(links.values()), groups_of(model, nodes))
    by_name = {node.name: node for node in nodes}
    for link in diagram.links:
        for name in (link.a, link.b):
            by_name[name].cables += len(link.cables)
    place(diagram)
    return diagram


def groups_of(model, nodes):
    """The buses, links and chains of the car, each with the nodes it touches.
    A chain touches the box a node is in, else the node itself. What is not a
    node of the diagram is left out."""
    known = {node.name for node in nodes}
    groups = []
    for kind, entries in (("bus", model.car.buses), ("link", model.car.links)):
        for name, entry in entries.items():
            members = [end for end in (entry.get("ends") or []) if end in known]
            groups.append(Group(name, kind, unique(members)))
    for name, chain in model.car.chains.items():
        members = [node.box or node.name for node in chain]
        groups.append(Group(name, "chain", unique([m for m in members if m in known])))
    return groups


def unique(names):
    """The names once each, in order."""
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def end_node(model, end):
    """The node a cable end is: its box for a connector, else the device."""
    found = model.connector(end)
    if found is not None:
        return found[0].name
    if model.is_device(end):
        return end
    return None


# --- default positions --------------------------------------------------------------

def place(diagram):
    """Give every node a position. A block is a box with its devices in a column
    beside it, so a cable to a device never crosses another device; blocks are
    laid out in rows, connected boxes next to each other in reading order.
    Devices on no box share a last block.

    No two cables may run on one line, so room is made for them: a node is as
    tall as it has cables to give each its own cell on a side, and the gap
    between a box and its devices has a line for every cable."""
    by_name = {node.name: node for node in diagram.nodes}
    for node in diagram.nodes:
        node.w, node.h = BOX_SIZE if node.kind == "box" else DEVICE_SIZE
        if node.kind == "device":
            node.h = max(node.h, node.cables + 1)

    boxes = [node for node in diagram.nodes if node.kind == "box"]
    devices = [node for node in diagram.nodes if node.kind == "device"]
    owner = device_owners(diagram, by_name)
    for device in devices:
        device.owner = owner.get(device.name)

    blocks = []
    for box in order_boxes(diagram, boxes):
        members = [d for d in devices if owner.get(d.name) == box.name]
        # a cell on the box's side for each cable to a device, and for half of
        # the rest, which have more sides to share
        beside = sum(device.cables for device in members)
        need = max(beside, math.ceil(box.cables / 2))
        box.h = max(box.h, 2 * math.ceil((need + 2) / 2))
        blocks.append((box, members, max(SIDE_GAP, beside + 3)))
    loose = [d for d in devices if d.name not in owner]
    if loose:
        blocks.append((None, loose, SIDE_GAP))

    columns = max(1, math.ceil(math.sqrt(len(blocks) * 1.5)))
    y = 0
    for start in range(0, len(blocks), columns):
        row = blocks[start:start + columns]
        height = 0
        x = 0
        for box, members, gap in row:
            height = max(height, place_block(box, members, x, y, gap))
            x += (box.w if box is not None else 0) + gap + DEVICE_SIZE[0] + BLOCK_GAP
        y += height + BLOCK_GAP


def place_block(box, members, x, y, gap):
    """Put a box at (x, y) and its devices in a column `gap` cells to its right.
    Returns the block's height."""
    left = x
    height = 0
    if box is not None:
        box.x, box.y = x, y
        left = x + box.w + gap
        height = box.h
    top = y
    for device in members:
        device.x = left
        device.y = top
        top += device.h + GAP
    if members:
        height = max(height, top - GAP - y)
    return height


def device_owners(diagram, by_name):
    """The box each device sits under: the box it shares the most wires with,
    the first one in reading order on a tie. A device with no box is absent."""
    weight = {}
    for link in diagram.links:
        for device, other in ((link.a, link.b), (link.b, link.a)):
            if by_name[device].kind == "device" and by_name[other].kind == "box":
                weight.setdefault(device, {})
                weight[device][other] = weight[device].get(other, 0) + max(link.wires, 1)
    order = [node.name for node in diagram.nodes]
    owner = {}
    for device, boxes in weight.items():
        owner[device] = max(boxes, key=lambda box: (boxes[box], -order.index(box)))
    return owner


def order_boxes(diagram, boxes):
    """The boxes in an order that keeps connected ones close: start from the
    box with the most wires, then follow the strongest link to a box not yet
    placed; a separate group starts from its own busiest box."""
    names = {box.name for box in boxes}
    strength = {name: {} for name in names}
    for link in diagram.links:
        if link.a in names and link.b in names:
            strength[link.a][link.b] = strength[link.a].get(link.b, 0) + link.wires
            strength[link.b][link.a] = strength[link.b].get(link.a, 0) + link.wires
    total = {name: sum(neighbours.values()) for name, neighbours in strength.items()}
    reading = [box.name for box in boxes]

    done = []
    while len(done) < len(boxes):
        left = [name for name in reading if name not in done]
        if not any(name in strength[d] for d in done for name in left):
            done.append(max(left, key=lambda name: (total[name], -reading.index(name))))
            continue
        best = max(((strength[d][name], -reading.index(name), name)
                    for d in done for name in left if name in strength[d]))
        done.append(best[2])
    by_name = {box.name: box for box in boxes}
    return [by_name[name] for name in done]
