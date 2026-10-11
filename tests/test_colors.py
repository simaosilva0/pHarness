"""Wire colors (CONFIG.md, Colors; STRUCT.md, config.yaml and cables)."""

from pharness.check import read_and_check
from pharness.project.colors import Colors

CONFIG = "config.yaml"
BATTERY = "boxes/battery.yaml"
BULKHEAD = "boxes/bulkhead.yaml"
REARHUB = "boxes/rearhub.yaml"

AUTO = "color: auto\n"
HV_PLUS = "{pin: '+', net: hv, type: hv:p, to: Inverter}"
REAR_A = "{pin: A, net: front_io, type: power:12v, to: RearHub, cable: Rear Power, at: pass}"
FRONT_A = "{pin: A, net: front_io, type: power:12v, to: Bulkhead, cable: Rear Power, at: vcu:out0}"


def problems(project):
    """The problems with their level and entry: [(rule, where, level, entry)]."""
    report = project.check()
    return [(p.rule, p.where, p.level, p.entry) for p in report.sorted_problems()]


def colors_of(project):
    """The color of every type, as the tool works them out."""
    _, model = read_and_check(project.root)
    return Colors(model.settings)


def fill(project, colors):
    """`color: fill`, with these colors."""
    lines = "".join(f"  {type_}: {color}\n" for type_, color in colors.items())
    project.replace(CONFIG, AUTO, "color: fill\ncolors:\n" + lines)


# --- palette and mode ---------------------------------------------------------------

def test_a_palette_that_does_not_exist(project):
    project.replace(CONFIG, "palette: striped\n", "palette: extended\n")
    assert project.broken() == [("palette-name", "config.yaml:31")]


def test_the_palette_left_out(project):
    project.replace(CONFIG, "palette: striped\n", "")
    assert project.broken() == [("config-fields", "config.yaml:4")]


def test_a_color_mode_that_does_not_exist(project):
    project.replace(CONFIG, AUTO, "color: manual\n")
    assert project.broken() == [("color-mode", "config.yaml:32")]


def test_fill_without_colors(project):
    project.replace(CONFIG, AUTO, "color: fill\n")
    assert project.broken() == [("config-fields", "config.yaml:32")]


def test_auto_with_colors(project):
    project.replace(CONFIG, AUTO, "color: auto\ncolors:\n  ground: black\n")
    assert project.broken() == [("config-fields", "config.yaml:32")]


def test_fill_with_any_colors_even_the_same_twice(project):
    fill(project, {"ground": "brown", "power:5v": "brown"})
    assert project.broken() == []


# --- color names ------------------------------------------------------------------

def test_a_color_that_is_not_in_the_palette(project):
    fill(project, {"ground": "gray"})
    assert project.broken() == [("color-name", "config.yaml:34")]


def test_a_stripe_of_its_own_color(project):
    fill(project, {"ground": "black/black"})
    assert project.broken() == [("color-name", "config.yaml:34")]


def test_no_stripes_on_a_solid_palette(project):
    project.replace(CONFIG, "palette: striped\n", "palette: solid\n")
    fill(project, {"ground": "black/white"})
    assert project.broken() == [("color-name", "config.yaml:34")]


def test_shades_only_on_a_shaded_palette(project):
    fill(project, {"chain:s3": "light blue"})
    assert project.broken() == [("color-name", "config.yaml:34")]
    project.replace(CONFIG, "palette: striped\n", "palette: shaded\n")
    assert project.broken() == []


def test_a_pin_color_that_is_not_in_the_palette(project):
    project.replace(REARHUB, "cable: Left Cooling, at: vcu:out6",
                    "cable: Left Cooling, color: Red, at: vcu:out6")
    assert project.broken() == [("color-name", "boxes/rearhub.yaml:62")]


# --- types under colors -----------------------------------------------------------

def test_a_color_for_a_type_of_no_kind(project):
    fill(project, {"power:48v": "red"})
    assert project.broken() == [("color-type", "config.yaml:34")]


def test_a_color_for_a_shield(project):
    fill(project, {"shield": "black"})
    assert project.broken() == [("color-type", "config.yaml:34")]


def test_a_color_for_a_chain_out(project):
    fill(project, {"chain:s3": "white", "chain:s99": "white"})
    assert project.broken() == [("color-type", "config.yaml:35")]


def test_strict_needs_every_type_on_a_wire(project):
    project.replace(CONFIG, AUTO, "color: strict\ncolors:\n  ground: black\n")
    broken = project.check().problems
    assert {p.rule for p in broken} == {"colors-complete"}
    assert all(p.where == "config.yaml:33" for p in broken)
    whats = [p.what for p in broken]
    assert "no color for power:12v" in whats
    assert "no color for ground" not in whats
    assert "no color for shield" not in whats
    assert "no color for hv:p" not in whats
    assert "no color for chain:s3" not in whats


# --- high voltage -----------------------------------------------------------------

def test_hv_in_another_color(project):
    fill(project, {"hv:p": "red"})
    assert problems(project) == [("hv-orange", "config.yaml:34", "error", "hv:p")]


def test_low_voltage_in_orange(project):
    fill(project, {"power:12v": "orange"})
    assert problems(project) == [("hv-orange", "config.yaml:34", "error", "power:12v")]


def test_an_hv_pin_in_another_color(project):
    project.replace(BATTERY, HV_PLUS, "{pin: '+', net: hv, type: hv:p, to: Inverter, color: red}")
    assert problems(project) == [("hv-orange", "boxes/battery.yaml:22", "error", "Battery.hv.+")]


def test_an_hv_pin_in_another_color_accepted(project):
    project.replace(BATTERY, HV_PLUS, "{pin: '+', net: hv, type: hv:p, to: Inverter, color: red}")
    project.replace(CONFIG, "accept: {}\n", "accept:\n  hv-orange:\n    Battery.hv.+: bought, red with orange sleeve\n")
    assert project.broken() == []


def test_orange_is_the_base_color(project):
    project.replace(BATTERY, HV_PLUS, "{pin: '+', net: hv, type: hv:p, to: Inverter, color: orange/black}")
    assert project.broken() == []
    project.replace(BATTERY, "color: orange/black}", "color: black/orange}")
    assert project.broken() == [("hv-orange", "boxes/battery.yaml:22")]


def test_a_listed_wire_in_orange(project):
    project.write("cables/hoop_link.yaml", """cable: Hoop Link
ends: [Left Shutdown Button, Right Shutdown Button]
wires:
  - {net: sdc, type: chain:s0, from: Left Shutdown Button, to: Right Shutdown Button, color: orange}
""")
    assert problems(project) == [("hv-orange", "cables/hoop_link.yaml:4", "error", None)]


# --- the two ends of a wire --------------------------------------------------------

def test_a_color_on_one_end_of_a_wire(project):
    project.replace(BULKHEAD, REAR_A, REAR_A.replace(", at: pass", ", color: blue, at: pass"))
    assert project.broken() == []


def test_the_same_color_on_both_ends(project):
    project.replace(BULKHEAD, REAR_A, REAR_A.replace(", at: pass", ", color: blue, at: pass"))
    project.replace(REARHUB, FRONT_A, FRONT_A.replace(", at:", ", color: blue, at:"))
    assert project.broken() == []


def test_two_colors_for_one_wire(project):
    project.replace(BULKHEAD, REAR_A, REAR_A.replace(", at: pass", ", color: blue, at: pass"))
    project.replace(REARHUB, FRONT_A, FRONT_A.replace(", at:", ", color: white, at:"))
    assert project.broken() == [("wire-color", "boxes/bulkhead.yaml:31")]


# --- the colors the tool picks -----------------------------------------------------

def test_each_type_its_own_color(project):
    colors = colors_of(project)
    assert colors.of_type("power:12v") == "red"
    assert colors.of_type("power:5v") == "red/white"
    assert colors.of_type("analog") == "white"
    assert colors.of_type("pwm") == "white/green"
    assert colors.of_type("spi:sck") == "violet/white"
    assert colors.of_type("ethernet:p") == "green/white"


def test_can_low_is_green(project):
    colors = colors_of(project)
    assert colors.of_type("can:h") == "yellow"
    assert colors.of_type("can:l") == "green"


def test_a_chain_is_one_color_and_hv_orange(project):
    colors = colors_of(project)
    assert {colors.of_type(f"chain:s{i}") for i in range(9)} == {"brown"}
    assert colors.of_type("hv:u") == "orange"
    assert colors.of_type("shield") is None


def test_the_tool_skips_colors_the_project_chose(project):
    fill(project, {"ground": "red"})
    colors = colors_of(project)
    assert colors.of_type("ground") == "red"
    assert colors.of_type("power:12v") == "red/white"
    assert not colors.is_picked("ground")
    assert colors.is_picked("power:12v")


def test_a_solid_palette_shares_the_base(project):
    project.replace(CONFIG, "palette: striped\n", "palette: solid\n")
    colors = colors_of(project)
    assert colors.of_type("power:5v") == "red"
    assert colors.of_type("can:l") == "green"
