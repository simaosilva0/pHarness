"""The car diagram: its nodes, links and default positions (diagram.py), and
the Car tab that carries them (page.py)."""

import json
import re

from pharness.check import read_and_check
from pharness.output.diagram import BOX_SIZE, DEVICE_SIZE, Diagram, Node
from pharness.output.page import render_car, render_page
from pharness.output.pinout import build_pinout


def pinout_of(project):
    report, model = read_and_check(project.root)
    assert report.errors() == []
    return model, build_pinout(model, report)


def diagram_of(project):
    return pinout_of(project)[1].diagram


def overlap(a, b):
    return (a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h)


def test_a_node_for_every_box_and_device(project):
    model, pinout = pinout_of(project)
    names = [node.name for node in pinout.diagram.nodes]
    assert names == [box.name for box in model.boxes] + list(model.car.devices)
    kinds = {node.name: node.kind for node in pinout.diagram.nodes}
    assert kinds["Nose"] == "box"
    assert kinds["IMU"] == "device"


def test_boxes_are_bigger_than_devices(project):
    for node in diagram_of(project).nodes:
        if node.kind == "box":
            assert node.w == BOX_SIZE[0] and node.h >= BOX_SIZE[1]
        else:
            assert (node.w, node.h) == DEVICE_SIZE


def test_no_two_nodes_overlap(project):
    nodes = diagram_of(project).nodes
    for index, node in enumerate(nodes):
        for other in nodes[index + 1:]:
            assert not overlap(node, other), (node.name, other.name)


def test_every_position_is_on_the_grid(project):
    for node in diagram_of(project).nodes:
        for value in (node.x, node.y, node.w, node.h):
            assert isinstance(value, int)


def test_a_cable_joins_the_box_of_its_connector_to_its_devices(project):
    links = {(link.a, link.b): link for link in diagram_of(project).links}
    link = links[("IMU", "Nose")]
    assert [cable.name for cable in link.cables] == ["IMU Lead"]
    assert link.wires == sum(cable.wires for cable in link.cables) > 0


def test_a_cable_inside_one_box_makes_no_link(project):
    for link in diagram_of(project).links:
        assert link.a != link.b


def test_cables_between_the_same_two_nodes_are_one_link(project):
    links = diagram_of(project).links
    pairs = [(link.a, link.b) for link in links]
    assert len(pairs) == len(set(pairs))
    bundled = [link for link in links if len(link.cables) > 1]
    assert bundled


def test_the_page_carries_the_diagram(project):
    model, pinout = pinout_of(project)
    page = render_page(pinout)
    found = re.search(r'<script type="application/json" id="car-data">(.*?)</script>', page)
    data = json.loads(found.group(1))
    assert data["grid"] == 20
    assert len(data["nodes"]) == len(pinout.diagram.nodes)
    assert '<svg id="car-svg"' in page


def test_a_name_cannot_end_the_data_tag():
    diagram = Diagram([Node("</script><b>", "device", "")], [])
    data = render_car(diagram).split('id="car-data">')[1].split("</script>")[0]
    assert "<" not in data
    assert json.loads(data)["nodes"][0]["name"] == "</script><b>"


def test_the_car_tab_has_its_switches_and_tooltip(project):
    page = render_page(pinout_of(project)[1])
    for id_ in ["car-show", "car-bundled", "car-reset", "car-tip"]:
        assert f'id="{id_}"' in page


def test_buses_links_and_chains_are_groups_of_nodes(project):
    model, pinout = pinout_of(project)
    names = {node.name for node in pinout.diagram.nodes}
    groups = {group.name: group for group in pinout.diagram.groups}
    assert set(groups) == set(model.car.buses) | set(model.car.links) | set(model.car.chains)
    assert groups["can_drive"].kind == "bus"
    assert groups["can_drive"].members == ["RearHub", "Battery", "Inverter"]
    assert groups["hvil"].kind == "chain"
    assert groups["hvil"].members == ["Battery", "Inverter", "ChargePort"]   # the box of each node
    for group in groups.values():
        assert set(group.members) <= names
        assert len(group.members) == len(set(group.members))


def test_a_device_knows_the_box_it_sits_beside(project):
    nodes = {node.name: node for node in diagram_of(project).nodes}
    assert nodes["APPS1"].owner == "Nose"
    assert nodes["Nose"].owner is None

