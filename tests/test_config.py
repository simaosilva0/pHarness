"""config.yaml (STRUCT.md, config.yaml; CONFIG.md: Styles, Types, Rule levels)."""

CONFIG = "config.yaml"


# --- fields ------------------------------------------------------------------

def test_an_unknown_field(project):
    project.add(CONFIG, "colour: auto\n")
    assert project.broken() == [("field-known", "config.yaml:54")]


def test_a_setting_left_out(project):
    project.replace(CONFIG, "accept: {}\n", "")
    assert project.broken() == [("config-fields", "config.yaml:4")]


def test_a_style_left_out(project):
    project.replace(CONFIG, "  board: snake\n", "")
    assert project.broken() == [("config-fields", "config.yaml:4")]


def test_a_kind_left_out(project):
    project.replace(CONFIG, "  serial:   {types: [serial], qualifiers: [tx, rx]}\n", "")
    assert ("config-fields", "config.yaml:14") in project.broken()


def test_a_kind_without_types(project):
    project.replace(CONFIG, "{types: [shield], label: shield}", "{label: shield}")
    assert ("config-fields", "config.yaml:26") in project.broken()
    assert ("kind-form", "config.yaml:26") not in project.broken()


def test_a_rule_left_out(project):
    project.replace(CONFIG, "  pin-order: warn\n", "")
    assert project.broken() == [("config-fields", "config.yaml:35")]


def test_a_field_of_the_wrong_shape(project):
    project.replace(CONFIG, "sides: [left, right, fl, fr, rl, rr]", "sides: left")
    assert project.broken() == [("field-shape", "config.yaml:12")]


# --- styles ------------------------------------------------------------------

def test_a_style_for_something_that_is_not_a_kind_of_name(project):
    project.replace(CONFIG, "  board: snake\n", "  board: snake\n  wire: snake\n")
    assert project.broken() == [("style-kind", "config.yaml:10")]


def test_a_style_that_does_not_exist(project):
    project.replace(CONFIG, "  box: pascal", "  box: lower")
    assert project.broken() == [("style-name", "config.yaml:6")]


def test_a_net_style_without_a_separator(project):
    project.replace(CONFIG, "  net: snake", "  net: pascal")
    assert project.broken() == [("style-net", "config.yaml:5")]


def test_a_side_in_another_case(project):
    project.replace(CONFIG, "sides: [left,", "sides: [Left,")
    assert project.broken() == [("net-words-case", "config.yaml:12")]


def test_a_qualifier_of_two_words(project):
    project.replace(CONFIG, "qualifiers: [12v, 5v]", "qualifiers: [12v, 5v, 48_v]")
    assert project.broken() == [("net-words-case", "config.yaml:15")]


# --- types -------------------------------------------------------------------

def test_a_kind_that_does_not_exist(project):
    project.replace(CONFIG, "  no_net:   {types: [spare, unfitted]}\n",
                    "  no_net:   {types: [spare, unfitted]}\n  usb:      {types: [usb], qualifiers: [dp, dm]}\n")
    assert project.broken() == [("type-kinds", "config.yaml:30")]


def test_a_kind_not_used(project):
    project.replace(CONFIG, "{types: [serial], qualifiers: [tx, rx]}", "{types: []}")
    broken = project.broken()
    assert [where for _, where in broken if where.startswith("config.yaml")] == []


def test_a_kind_not_used_with_qualifiers(project):
    project.replace(CONFIG, "{types: [serial], qualifiers: [tx, rx]}", "{types: [], qualifiers: [tx, rx]}")
    assert ("kind-form", "config.yaml:25") in project.broken()


def test_a_kind_with_a_label_and_qualifiers(project):
    project.replace(CONFIG, "{types: [ground], label: gnd}", "{types: [ground], label: gnd, qualifiers: [a]}")
    assert project.broken() == [("kind-form", "config.yaml:16")]


def test_a_chain_with_a_label(project):
    project.replace(CONFIG, "{types: [chain]}", "{types: [chain], label: sdc}")
    assert project.broken() == [("kind-form", "config.yaml:28")]


def test_a_type_word_in_capitals(project):
    project.replace(CONFIG, "pwm, freq, sent]", "pwm, freq, sent, PSI5]")
    assert project.broken() == [("type-word-case", "config.yaml:17")]


def test_a_type_word_in_two_kinds_with_qualifiers(project):
    project.replace(CONFIG, "{types: [analog, hv], qualifiers: [p, n]}", "{types: [analog, hv, power], qualifiers: [p, n]}")
    assert project.broken() == [("type-word-twice", "config.yaml:15")]


def test_hv_may_be_in_pair_and_phase(project):
    assert "  phase:    {types: [hv]" in (project.root / CONFIG).read_text()
    assert project.broken() == []


def test_spare_outside_no_net(project):
    project.replace(CONFIG, "{types: [shield], label: shield}", "{types: [shield, spare], label: shield}")
    assert project.broken_rules() == ["type-reserved", "type-word-twice"]



# --- ethernet pairs -----------------------------------------------------------

ETHERNET = "  ethernet: {types: [ethernet], qualifiers: [p, n]}\n"
RJ45 = "  ethernet: {types: [ethernet], qualifiers: [1, 2, 3, 4, 5, 6, 7, 8]%s}\n"


def eth_pairs(project):
    return [one for one in project.broken() if one[0] == "eth-pairs"]


def test_two_qualifiers_are_one_pair(project):
    project.replace(CONFIG, ETHERNET, "  ethernet: {types: [ethernet], qualifiers: [p, n], pairs: [[p, n]]}\n")
    assert project.broken() == [("eth-pairs", "config.yaml:27")]


def test_rj45_qualifiers_need_their_pairs(project):
    # The pins on eth_logger are ethernet:p and :n, so pin-type breaks too.
    project.replace(CONFIG, ETHERNET, RJ45 % "")
    assert eth_pairs(project) == [("eth-pairs", "config.yaml:27")]


def test_rj45_qualifiers_in_t568_pairs(project):
    project.replace(CONFIG, ETHERNET, RJ45 % ", pairs: [[1, 2], [3, 6], [4, 5], [7, 8]]")
    assert eth_pairs(project) == []


def test_a_qualifier_in_two_pairs_or_none(project):
    project.replace(CONFIG, ETHERNET, RJ45 % ", pairs: [[1, 2], [2, 3], [4, 5], [7, 8]]")
    assert eth_pairs(project) == [("eth-pairs", "config.yaml:27")]


def test_pairs_only_on_ethernet(project):
    project.replace(CONFIG, "{types: [can], qualifiers: [h, l]}", "{types: [can], qualifiers: [h, l], pairs: [[h, l]]}")
    assert project.broken() == [("eth-pairs", "config.yaml:20")]


# --- rule levels -------------------------------------------------------------

def test_rule_levels(project):
    project.replace(CONFIG, "  pin-order: warn\n", "  pin-order: off\n")
    project.replace(CONFIG, "  device-used: warn\n", "  device-used: error\n")
    assert project.broken() == []


def test_a_rule_that_does_not_exist(project):
    project.replace(CONFIG, "  pin-order: warn\n", "  pin-order: warn\n  pin-orders: off\n")
    assert project.broken() == [("rule-known", "config.yaml:47")]


def test_a_level_that_does_not_exist(project):
    project.replace(CONFIG, "  pin-order: warn\n", "  pin-order: pass\n")
    assert project.broken() == [("rule-level", "config.yaml:46")]


def test_a_fixed_rule_cannot_change(project):
    project.replace(CONFIG, "  pin-order: warn\n", "  pin-order: warn\n  net-style: warn\n")
    assert project.broken() == [("rule-fixed", "config.yaml:47")]


# --- accepted entries ----------------------------------------------------------

def test_an_accepted_entry_needs_a_reason(project):
    project.replace(CONFIG, "accept: {}\n", "accept:\n  to-reaches:\n    Nose.harness.A: ''\n")
    assert ("accept-reason", "config.yaml:55") in project.broken()


def test_a_fixed_rule_cannot_be_accepted(project):
    project.replace(CONFIG, "accept: {}\n", "accept:\n  net-style:\n    foo: no reason needed\n")
    assert project.broken() == [("rule-fixed", "config.yaml:54")]
