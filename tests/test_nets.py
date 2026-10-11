"""Nets and types on pins (CONFIG.md: Nets, Types, Buses, Ethernet, Chains).

A renamed net also leaves its conductor with one end, so these tests check
that the rule broke where expected, not that nothing else did.
"""

NOSE = "boxes/nose.yaml"
APPS1_SIGNAL = "{pin: '3', net: apps1, type: analog,"


def plant_net(project, net):
    project.replace(NOSE, APPS1_SIGNAL, f"{{pin: '3', net: {net}, type: analog,")


def test_a_net_in_another_style(project):
    plant_net(project, "Apps1")
    assert ("net-style", "boxes/nose.yaml:11") in project.broken()


def test_a_net_starting_with_a_digit(project):
    plant_net(project, "1apps")
    assert ("net-letter", "boxes/nose.yaml:11") in project.broken()


def test_a_side_after_the_first_word(project):
    plant_net(project, "apps1_left")
    assert ("net-side-first", "boxes/nose.yaml:11") in project.broken()


def test_a_net_that_is_only_a_side_and_an_index(project):
    plant_net(project, "left_1")
    assert ("net-thing", "boxes/nose.yaml:11") in project.broken()


def test_a_net_ending_in_its_label(project):
    plant_net(project, "apps1_sig")
    assert ("net-no-label", "boxes/nose.yaml:11") in project.broken()


def test_a_net_ending_in_an_index(project):
    plant_net(project, "apps1_2")
    rules = project.broken_rules()
    assert "net-no-label" not in rules
    assert "net-thing" not in rules


def test_a_net_named_like_a_bus(project):
    plant_net(project, "can_apps1")
    assert ("bus-net", "boxes/nose.yaml:11") in project.broken()


def test_a_net_named_like_a_link(project):
    plant_net(project, "eth_apps1")
    assert ("eth-net", "boxes/nose.yaml:11") in project.broken()


def test_a_bus_pin_of_another_bus_kind(project):
    project.replace(NOSE, "net: can_chassis, type: can:h, to: IMU}", "net: can_chassis, type: lin, to: IMU}")
    assert ("bus-type", "boxes/nose.yaml:60") in project.broken()


def test_a_type_with_a_qualifier_not_in_its_kind(project):
    project.replace(NOSE, "net: imu, type: power:12v, to: IMU}", "net: imu, type: power:48v, to: IMU}")
    assert ("pin-type", "boxes/nose.yaml:58") in project.broken()


def test_a_chain_pin_with_an_out_the_chain_does_not_have(project):
    project.replace(NOSE, "net: sdc, type: chain:s4, to: BOTS}", "net: sdc, type: chain:s9, to: BOTS}")
    assert ("chain-type", "boxes/nose.yaml:39") in project.broken()


def test_an_ethernet_pin_off_a_link(project):
    project.replace("boxes/rearhub.yaml", "net: logger, type: power:12v", "net: logger, type: ethernet:p")
    assert "eth-type" in project.broken_rules()
