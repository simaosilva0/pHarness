"""Reading the files (STRUCT.md, Files)."""

from pharness.project.load import Loader
from pharness.rules.report import Report


def test_kestrel_has_no_problems(project):
    assert project.broken() == []


def test_a_key_written_twice(project):
    project.replace("config.yaml", "  board: snake\n", "  board: snake\n  board: snake\n")
    assert project.broken() == [("key-once", "config.yaml:10")]


def test_a_tab_is_not_yaml(project):
    project.replace("boxes/nose.yaml", "box: Nose\n", "box: Nose\n\tnote: x\n")
    assert project.broken_rules() == ["yaml"]


def test_a_missing_car_yaml(project):
    project.remove("car.yaml")
    assert project.broken() == [("yaml", "car.yaml")]


def test_a_box_file_that_is_a_list(project):
    project.write("boxes/nose.yaml", "- box: Nose\n")
    assert project.broken() == [("yaml", "boxes/nose.yaml")]


def read(text):
    loader = Loader(text, "test.yaml", Report())
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def test_only_true_and_false_are_booleans():
    data = read("a: off\nb: no\nc: on\nd: yes\ne: true\nf: false\n")
    assert data == {"a": "off", "b": "no", "c": "on", "d": "yes", "e": True, "f": False}


def test_every_key_has_its_line():
    data = read("a: 1\nb:\n  c: 2\n")
    assert data.line == 1
    assert data.at == {"a": 1, "b": 2}
    assert data["b"].at == {"c": 3}
