"""Accepted entries (CONFIG.md, Rule levels)."""

from pharness.checks.accept import entries_by_rule
from pharness.checks.config import adjustable_rules, check_config
from pharness.project.load import load_project
from pharness.project.read import read_model
from pharness.rules.report import Report

CAR = "car.yaml"
CONFIG = "config.yaml"
NOSE = "boxes/nose.yaml"


def accept(project, rule, entry, reason="known, kept on purpose"):
    """Accept one entry under one rule; the entry is on config.yaml:45."""
    project.replace(CONFIG, "accept: {}\n", f"accept:\n  {rule}:\n    {entry}: {reason}\n")


def problems(project):
    report = project.check()
    return [(p.rule, p.where, p.level) for p in report.sorted_problems()]


def test_every_adjustable_rule_names_its_entries(project):
    report = Report()
    loaded = load_project(project.root, report)
    model = read_model(loaded, check_config(loaded.config, report), report)
    assert sorted(entries_by_rule(model)) == sorted(adjustable_rules())


def test_an_accepted_entry_is_not_reported(project):
    project.replace(NOSE, "{pin: '2', type: spare}", "{pin: '2', net: horn, type: digital}")
    accept(project, "conductor-one-end", "horn digital")
    assert project.broken() == []


def test_an_accepted_entry_that_does_not_exist(project):
    accept(project, "to-reaches", "Nose.harness.Z")
    assert project.broken() == [("accept-known", "config.yaml:48")]


def test_an_accepted_entry_that_no_longer_breaks_its_rule(project):
    accept(project, "to-reaches", "Nose.harness.A")
    assert problems(project) == [("accept-used", "config.yaml:48", "warn")]


def test_an_accepted_pin_its_rule_is_not_about(project):
    # pedals 1 goes to a device: to-reaches is about pins going to a box.
    accept(project, "to-reaches", "Nose.pedals.1")
    assert problems(project) == [("accept-used", "config.yaml:48", "warn")]


def test_an_accepted_entry_under_a_rule_turned_off(project):
    project.replace(CONFIG, "  to-reaches: error\n", "  to-reaches: off\n")
    accept(project, "to-reaches", "Nose.harness.A")
    assert project.broken() == []


def test_an_accepted_entry_its_rule_skipped(project):
    # The misspelled end is the one mistake: ends-match does not run, so
    # whether can_charge still breaks it is not known.
    project.replace(CAR, "ends: [Battery, Charger]", "ends: [Battery, Charger Port]")
    accept(project, "ends-match", "can_charge")
    assert project.broken() == [("ends-known", "car.yaml:40")]


def test_an_accepted_pin_going_nowhere_known(project):
    project.replace(NOSE, "{pin: A, net: front_io, type: power:12v, to: Bulkhead}",
                    "{pin: A, net: front_io, type: power:12v, to: Bulkhed}")
    accept(project, "to-reaches", "Nose.harness.A")
    assert project.broken() == [("to-known", "boxes/nose.yaml:73")]


def test_accepted_entries_while_a_box_has_no_name(project):
    project.replace(NOSE, "box: Nose\n", "")
    accept(project, "to-reaches", "Nose.harness.A")
    assert project.broken_rules() == ["box-fields"]
