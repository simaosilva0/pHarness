"""The pinout page (page.py) and `pharness build` (cli.py)."""

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
    assert "7 boxes · 33 connectors · 216 pins" in page
    assert page.count('<section class="box"') == 7
    assert page.count('<tr id="boxes-') == 216


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
    assert "<strong>1 warning</strong>" in page
    assert '<a href="#boxes-nose-yaml-43">' in page
    assert '<tr id="boxes-nose-yaml-43" class="warned">' in page
    assert '<span class="warning">conductor-one-end: horn digital: ' in page


def test_no_warnings_no_list(project):
    assert 'class="warnings"' not in page_of(project)


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

