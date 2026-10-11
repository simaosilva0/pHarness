"""The pinout page (page.py) and `pharness build` (cli.py)."""

import re
import shutil

from pharness.check import read_and_check
from pharness.cli import main
from pharness.output.page import render_page
from pharness.output.pinout import build_pinout

NOSE = "boxes/nose.yaml"
BATTERY = "boxes/battery.yaml"
SPARE = "{pin: '2', type: spare}"   # Nose bots 2, boxes/nose.yaml:43


def page_of(project):
    report, model = read_and_check(project.root)
    assert report.errors() == []
    return render_page(build_pinout(model, report))


# --- the page --------------------------------------------------------------------

def test_the_page_has_every_box_and_pin(project):
    page = page_of(project)
    assert page.startswith("<!doctype html>")
    assert "<title>Kestrel pinout</title>" in page
    assert "7 boxes · 33 connectors · 216 pins · 28 cables · 150 wires" in page
    assert page.count('<section class="box"') == 7
    assert page.count('<tr id="boxes-') == 216
    assert page.count('<section class="cable"') == 28


def test_the_page_needs_nothing_from_outside(project):
    page = page_of(project)
    assert "<script" not in page
    assert "http" not in page


def test_a_to_a_box_links_to_it_and_a_device_does_not(project):
    page = page_of(project)
    assert '<section class="box" id="boxes-rearhub-yaml">' in page
    assert '<a href="#boxes-rearhub-yaml">RearHub</a>' in page
    assert '<a href="#boxes-imu' not in page


def test_spare_pins_are_greyed(project):
    page = page_of(project)
    assert '<tr id="boxes-battery-yaml-17" class="unused">' in page


def test_text_is_escaped(project):
    project.replace(BATTERY, "note: into the IMD relay}", "note: 'a <b> & c'}")
    page = page_of(project)
    assert "a &lt;b&gt; &amp; c" in page
    assert "a <b>" not in page


def test_a_warning_is_listed_and_marked_on_its_pin(project):
    project.replace(NOSE, SPARE, "{pin: '2', net: horn, type: digital}")
    page = page_of(project)
    assert "<h2>1 warning</h2>" in page
    assert '<a href="#warnings">Warnings (1)</a>' in page
    assert '<a href="#boxes-nose-yaml-43">' in page
    assert '<tr id="boxes-nose-yaml-43" class="warned">' in page
    assert '<span class="warning">conductor-one-end: horn digital: ' in page


def test_no_warnings_no_list(project):
    page = page_of(project)
    assert 'class="warnings"' not in page
    assert "No warnings." in page


def test_the_page_has_four_tabs(project):
    page = page_of(project)
    assert ('<nav class="tabs"><a href="#boxes">Boxes (7)</a><a href="#cables">Cables (28)</a>'
            '<a href="#warnings">Warnings (0)</a><a href="#config">Config</a></nav>') in page
    for name in ["boxes", "cables", "config", "warnings"]:
        assert f'<section class="panel" id="{name}">' in page


# --- pharness build ----------------------------------------------------------------

def test_build_writes_the_page_in_the_project(project):
    assert main(["build", str(project.root)]) == 0
    page = project.root / "build" / "pinout.html"
    assert page.read_text().startswith("<!doctype html>")


def test_build_writes_where_it_is_told(project, tmp_path):
    output = tmp_path / "out" / "kestrel.html"
    assert main(["build", str(project.root), "-o", str(output)]) == 0
    assert output.exists()
    assert not (project.root / "build").exists()


def test_build_writes_with_warnings(project):
    project.replace(NOSE, SPARE, "{pin: '2', net: horn, type: digital}")
    assert main(["build", str(project.root)]) == 0
    assert (project.root / "build" / "pinout.html").exists()


def test_build_writes_nothing_with_an_error(project, capsys):
    project.replace(NOSE, "box: Nose\n", "box: nose\n")
    assert main(["build", str(project.root)]) == 1
    assert not (project.root / "build").exists()
    assert "nothing written" in capsys.readouterr().out


# --- cables and colors -------------------------------------------------------------

def test_a_far_pin_links_to_its_row(project):
    page = page_of(project)
    assert '<a href="#boxes-bulkhead-yaml-37">Bulkhead.rear.G</a>' in page
    assert '<tr id="boxes-bulkhead-yaml-37">' in page


def test_a_cable_links_to_its_section(project):
    page = page_of(project)
    assert '<a href="#cables-rear-signal-yaml">Rear Signal</a>' in page
    assert '<section class="cable" id="cables-rear-signal-yaml">' in page


def test_a_color_has_a_swatch_and_picked_is_italic(project):
    page = page_of(project)
    assert '<span class="swatch" style="background: #fdd835"></span><span class="picked">yellow</span>' in page
    assert "linear-gradient(135deg, #1e63c6 38%, #ffffff 38% 62%, #1e63c6 62%)" in page


def test_a_chosen_color_is_not_italic(project):
    project.replace("config.yaml", "color: auto\n", "color: fill\ncolors:\n  ground: brown\n")
    page = page_of(project)
    assert '<span class="swatch" style="background: #7b4a26"></span>brown</td>' in page


def test_a_cable_named_like_a_box_links_to_the_cable(project):
    project.remove("cables/imu_lead.yaml")
    project.write("cables/nose.yaml", "cable: Nose\nends: [Nose.imu, IMU]\n")
    project.replace("boxes/nose.yaml", "    cable: IMU Lead\n", "    cable: Nose\n")
    page = page_of(project)
    assert '<a href="#cables-nose-yaml">Nose</a>' in page
    assert '<a href="#boxes-nose-yaml">Nose</a>' in page


def test_without_cables_no_cable_section(project):
    shutil.rmtree(project.root / "cables")
    for path in (project.root / "boxes").glob("*.yaml"):
        text = re.sub(r"\n    cable: [^\n]*", "", path.read_text())
        path.write_text(re.sub(r", cable: [^,}]*", "", text))
    page = page_of(project)
    assert 'id="cables"' not in page
    assert 'id="config"' not in page
    assert "216 pins</div>" in page
