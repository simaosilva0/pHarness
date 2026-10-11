"""Building the model from the loaded files (STRUCT.md).

Reading reports every field of the wrong shape once, here, and leaves it out
of the model, so the checks after it never meet a list where they expect text.
"""

from .fields import check_fields, get_list, get_map, is_map, is_text_name
from .load import Map
from .model import Box, Car, Connector, Model, Node, Pin

CAR_FILE = "car.yaml"
CAR_FIELDS = ["car", "devices", "buses", "links", "chains"]
DEVICE_FIELDS = ["note"]
BUS_FIELDS = ["bitrate", "data_bitrate", "ends", "internal"]
LINK_FIELDS = ["ends"]
NODE_FIELDS = ["node", "out", "box"]

BOX_FIELDS = ["box", "boards", "note", "connectors"]
CONNECTOR_FIELDS = ["part", "note", "pins"]
PIN_FIELDS = ["pin", "net", "type", "to", "at", "note"]
PIN_TEXT_FIELDS = ["net", "type", "to", "at", "note"]   # `pin` has its own rule


def read_model(project, settings, report):
    car = read_car(project.car, report)
    boxes = [read_box(box, report) for box in project.boxes]
    return Model(settings, car, boxes, project.unread)


# --- car.yaml ------------------------------------------------------------------

def read_car(data, report):
    check_fields(data, CAR_FIELDS, CAR_FILE, "car", report)
    devices = read_entries(data, "devices", DEVICE_FIELDS, report)
    buses = read_entries(data, "buses", BUS_FIELDS, report)
    links = read_entries(data, "links", LINK_FIELDS, report)
    chains = read_chains(data, report)
    return Car(data, devices, buses, links, chains)


def read_entries(data, group, allowed, report):
    """The entries under `devices`, `buses` or `links`: name -> Map.
    An entry written with nothing (`APPS1:`) is an empty one."""
    entries = {}
    group_map = get_map(data, group, CAR_FILE, report)
    for name, entry in group_map.items():
        line = group_map.at[name]
        if not is_text_name(name, CAR_FILE, line, f"{group} name", report):
            continue
        if entry is None:
            entry = Map(line)
        if not is_map(entry, CAR_FILE, line, f"{group} {name}", report):
            continue
        check_fields(entry, allowed, CAR_FILE, f"{name}", report)
        if "ends" in entry:
            entry["ends"] = get_list(entry, "ends", CAR_FILE, report)
        entries[name] = entry
    return entries


def read_chains(data, report):
    """Every chain: name -> its nodes, in the order current flows."""
    chains = {}
    chains_map = get_map(data, "chains", CAR_FILE, report)
    for name in chains_map:
        if not is_text_name(name, CAR_FILE, chains_map.at[name], "chain name", report):
            continue
        nodes = []
        for node in get_list(chains_map, name, CAR_FILE, report):
            line = chains_map.at[name]
            if not is_map(node, CAR_FILE, line, f"a node of {name}", report):
                continue
            check_fields(node, NODE_FIELDS, CAR_FILE, f"{name} node", report)
            nodes.append(Node(name, node, f"{CAR_FILE}:{node.line}"))
        chains[name] = nodes
    return chains


# --- boxes/<box>.yaml ------------------------------------------------------------

def read_box(loaded, report):
    data = loaded.data
    file = loaded.name
    check_fields(data, BOX_FIELDS, file, "box", report)
    boards = get_list(data, "boards", file, report)
    box = Box(data.get("box"), file, loaded.path, data, boards)

    connectors = get_map(data, "connectors", file, report)
    for name, connector_data in connectors.items():
        line = connectors.at[name]
        if not is_text_name(name, file, line, "connector name", report):
            continue
        if connector_data is None:
            connector_data = Map(line)
        if not is_map(connector_data, file, line, f"connector {name}", report):
            continue
        check_fields(connector_data, CONNECTOR_FIELDS, file, f"connector {name}", report)
        connector = Connector(name, connector_data, f"{file}:{line}")
        connector.pins = read_pins(box, connector, report)
        box.connectors.append(connector)

    return box


def read_pins(box, connector, report):
    pins = []
    for pin_data in get_list(connector.data, "pins", box.file, report):
        if not is_map(pin_data, box.file, connector.data.at["pins"], f"a pin of {connector.name}", report):
            continue
        at = f"{box.file}:{pin_data.line}"
        check_fields(pin_data, PIN_FIELDS, box.file, f"pin {pin_data.get('pin')}", report)
        drop_fields_that_are_not_text(pin_data, PIN_TEXT_FIELDS, at, report)
        pins.append(Pin(box.name, connector.name, pin_data, at))
    return pins


# --- helpers -------------------------------------------------------------------

def drop_fields_that_are_not_text(data, names, at, report):
    """field-shape on text fields. A field that is not text is left out of the
    model, as if it was never written."""
    for name in names:
        if name not in data:
            continue
        is_text = isinstance(data[name], str)
        if not report.check("field-shape", is_text, at, f"{name} is not text"):
            del data[name]
