"""car.yaml (STRUCT.md, car.yaml; CONFIG.md: Buses, Ethernet, Chains)."""

CAR = "car.yaml"


def test_a_car_without_a_name(project):
    project.replace(CAR, "car: Kestrel\n", "")
    assert project.broken_rules() == ["car-name"]


def test_a_device_name_in_another_style(project):
    project.replace(CAR, "  APPS2: {}\n", "  APPS2: {}\n  apps 3: {}\n")
    assert ("device-style", "car.yaml:6") in project.broken()


def test_a_device_named_with_a_number(project):
    project.replace(CAR, "  APPS2: {}\n", "  APPS2: {}\n  3: {}\n")
    assert ("field-shape", "car.yaml:6") in project.broken()


def test_a_device_that_is_also_a_box(project):
    project.replace(CAR, "  APPS2: {}\n", "  APPS2: {}\n  Inverter: {}\n")
    assert ("box-not-device", "car.yaml:6") in project.broken()


def test_a_bus_that_is_not_a_bus_kind(project):
    project.replace(CAR, "links:\n", "  gps_bus: {bitrate: 9600, ends: [Logger]}\n\nlinks:\n")
    assert ("bus-name", "car.yaml:46") in project.broken()


def test_a_bus_without_a_bitrate(project):
    project.replace(CAR, "can_charge: {bitrate: 250000, ends:", "can_charge: {ends:")
    assert project.broken() == [("bus-fields", "car.yaml:40")]


def test_a_data_bitrate_off_can(project):
    project.replace(CAR, "lin_wheel: {bitrate: 19200,", "lin_wheel: {bitrate: 19200, data_bitrate: 38400,")
    assert project.broken() == [("bus-fields", "car.yaml:41")]


def test_a_bitrate_that_is_not_a_whole_number(project):
    project.replace(CAR, "lin_wheel: {bitrate: 19200,", "lin_wheel: {bitrate: 19.2k,")
    assert project.broken() == [("bus-fields", "car.yaml:41")]


def test_a_link_that_is_not_eth(project):
    project.replace(CAR, "  eth_logger: {ends: [RearHub, Logger]}\n",
                    "  eth_logger: {ends: [RearHub, Logger]}\n  logger_link: {ends: [RearHub, Logger]}\n")
    assert ("eth-link-name", "car.yaml:48") in project.broken()


def test_a_chain_node_without_an_out(project):
    project.replace(CAR, "{node: TSMS, out: s8}", "{node: TSMS}")
    assert ("chain-fields", "car.yaml:59") in project.broken()


def test_two_nodes_with_the_same_out(project):
    project.replace(CAR, "{node: TSMS, out: s8}", "{node: TSMS, out: s7}")
    broken = project.broken()
    assert ("chain-out-unique", "car.yaml:58") in broken
    assert ("chain-out-unique", "car.yaml:59") in broken


def test_a_chain_out_in_another_case(project):
    project.replace(CAR, "{node: TSMS, out: s8}", "{node: TSMS, out: S8}")
    assert ("net-words-case", "car.yaml:59") in project.broken()


def test_a_node_in_a_box_that_does_not_exist(project):
    project.replace(CAR, "{node: IMD, out: s6, box: Battery}", "{node: IMD, out: s6, box: Batery}")
    assert project.broken() == [("chain-node", "car.yaml:57")]


def test_a_node_outside_every_box_that_is_not_a_device(project):
    project.replace(CAR, "{node: TSMS, out: s8}", "{node: TSMS Switch, out: s8}")
    assert ("chain-node", "car.yaml:59") in project.broken()


def test_a_node_in_a_box_named_in_another_style(project):
    project.replace(CAR, "{node: IMD, out: s6, box: Battery}", "{node: imd, out: s6, box: Battery}")
    assert project.broken() == [("device-style", "car.yaml:57")]
