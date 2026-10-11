"""car.yaml (STRUCT.md, car.yaml; CONFIG.md: Buses, Ethernet, Chains)."""

from ..project.settings import BUS_KINDS
from ..project.styles import is_net_word
from .names import check_style

FILE = "car.yaml"


def check_car(model, nets, report):
    car = model.car
    report.check("car-name", "car" in car.data, f"{FILE}:{car.data.line}", "car has no name")
    check_devices(model, report)
    check_buses(model, nets, report)
    check_links(model, nets, report)
    check_chains(model, nets, report)


def check_devices(model, report):
    """device-style, box-not-device."""
    style = model.settings.style["device"]
    devices = model.car.data.get("devices")
    for name in model.car.devices:
        at = f"{FILE}:{devices.at[name]}"
        check_style(report, "device-style", name, style, at, "device")
        report.check("box-not-device", not model.is_box(name), at, f"{name} is a device and a box")


def check_buses(model, nets, report):
    """bus-name and bus-fields, and the Nets rules on every bus's name."""
    buses = model.car.data.get("buses")
    for name, bus in model.car.buses.items():
        at = f"{FILE}:{buses.at[name]}"
        nets.check_net(name, at)

        words = nets.words(name)
        is_bus_name = words[0].lower() in BUS_KINDS and len(words) > 1
        report.check("bus-name", is_bus_name, at, f"bus {name} is not a bus kind and a name")

        is_can = words[0].lower() == "can"
        problems = bus_field_problems(bus, ["bitrate", "ends"], is_can)
        report.check("bus-fields", not problems, at, f"bus {name}: {'; '.join(problems)}")


def check_links(model, nets, report):
    """eth-link-name and bus-fields, and the Nets rules on every link's name."""
    links = model.car.data.get("links")
    for name, link in model.car.links.items():
        at = f"{FILE}:{links.at[name]}"
        nets.check_net(name, at)

        words = nets.words(name)
        is_link_name = words[0].lower() == "eth" and len(words) > 1
        report.check("eth-link-name", is_link_name, at, f"link {name} is not ETH and a name")

        problems = bus_field_problems(link, ["ends"], is_can=False)
        report.check("bus-fields", not problems, at, f"link {name}: {'; '.join(problems)}")


def bus_field_problems(entry, required, is_can):
    """What is wrong with the fields of a bus or link, as a list of reasons."""
    problems = []
    for name in required:
        if name not in entry:
            problems.append(f"no {name}")
    if "data_bitrate" in entry and not is_can:
        problems.append("data_bitrate is only on a CAN bus")
    for rate in ["bitrate", "data_bitrate"]:
        if rate in entry and not is_positive_whole_number(entry[rate]):
            problems.append(f"{rate} is not a whole number above 0")
    if entry.get("internal", True) is not True:
        problems.append("internal is only ever true")
    return problems


def is_positive_whole_number(value):
    return type(value) is int and value > 0


def check_chains(model, nets, report):
    """The Nets rules on every chain's name; chain-fields, chain-out-unique,
    chain-node, and the out and node names of every node."""
    net_style = model.settings.style["net"]
    device_style = model.settings.style["device"]
    chains = model.car.data.get("chains")

    for chain, nodes in model.car.chains.items():
        nets.check_net(chain, f"{FILE}:{chains.at[chain]}")
        outs = [node.out for node in nodes]

        for node in nodes:
            has_fields = "node" in node.data and "out" in node.data
            report.check("chain-fields", has_fields, node.where, f"{chain} node {node.name} needs node and out")
            report.check("chain-out-unique", outs.count(node.out) == 1, node.where,
                         f"{chain} out {node.out} is on more than one node")
            if net_style is not None:
                report.check("net-words-case", is_net_word(node.out, net_style), node.where,
                             f"{chain} out {node.out} is not one {net_style} word")
            check_node_place(model, node, device_style, report)


def check_node_place(model, node, device_style, report):
    """chain-node: a node in a box names that box, a node outside every box is a
    device. A node in a box is named like a device, after the part it is."""
    if node.box is None:
        report.check("chain-node", model.is_device(node.name), node.where,
                     f"{node.chain} node {node.name} is not a device, and has no box")
        return
    report.check("chain-node", model.is_box(node.box), node.where,
                 f"{node.chain} node {node.name}: there is no box {node.box}")
    check_style(report, "device-style", node.name, device_style, node.where, f"{node.chain} node")
