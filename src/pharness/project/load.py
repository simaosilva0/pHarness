"""Reading a project (STRUCT.md, Files).

Every file is read as YAML 1.2, with the line of every mapping and key, so each
problem points at its file and line. Problems are collected, never raised: a
broken file is reported and the others are still read.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

BOOL = "tag:yaml.org,2002:bool"
MAP = "tag:yaml.org,2002:map"


class Map(dict):
    """A YAML mapping that remembers its line and the line of each key."""

    def __init__(self, line):
        super().__init__()
        self.line = line
        self.at = {}   # key -> line


class Loader(yaml.SafeLoader):
    """PyYAML's safe loader, reading YAML 1.2 booleans and building Maps."""

    def __init__(self, stream, name, report):
        super().__init__(stream)
        self.name = name       # the file's path from the project, for reports
        self.report = report


def only_true_and_false_are_booleans():
    """YAML 1.2: only `true` and `false` are booleans, so `off`, `no` and `on`
    stay words. PyYAML follows YAML 1.1, which reads them as booleans."""
    resolvers = {}
    for first_char, rules in yaml.SafeLoader.yaml_implicit_resolvers.items():
        resolvers[first_char] = [rule for rule in rules if rule[0] != BOOL]
    Loader.yaml_implicit_resolvers = resolvers
    Loader.add_implicit_resolver(BOOL, re.compile(r"^(?:true|false)$"), ["t", "f"])


def construct_map(loader, node):
    """A mapping as a Map, reporting a key written twice."""
    m = Map(node.start_mark.line + 1)
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        line = key_node.start_mark.line + 1
        where = f"{loader.name}:{line}"
        loader.report.check("key-once", key not in m, where, f"{key} written twice")
        m[key] = loader.construct_object(value_node, deep=True)
        m.at[key] = line
    return m


only_true_and_false_are_booleans()
Loader.add_constructor(MAP, construct_map)


def describe_yaml_error(error, name):
    """Where a YAML error is and what it says, from PyYAML's exception."""
    mark = getattr(error, "problem_mark", None)
    where = name
    if mark is not None:
        where = f"{name}:{mark.line + 1}"

    what = getattr(error, "problem", None)
    if not what:
        what = str(error).splitlines()[0]
    return where, what


def load(path, root, report):
    """One file as a Map, or None when it is missing, broken or not a mapping."""
    name = path.relative_to(root).as_posix()
    if not report.check("yaml", path.is_file(), name, "missing"):
        return None

    with open(path, encoding="utf-8") as f:
        loader = Loader(f, name, report)
        try:
            data = loader.get_single_data()
        except yaml.YAMLError as error:
            where, what = describe_yaml_error(error, name)
            report.check("yaml", False, where, what)
            return None
        finally:
            loader.dispose()

    if not report.check("yaml", isinstance(data, Map), name, "not a mapping of fields"):
        return None
    return data


@dataclass
class Box:
    """One box file."""

    path: Path
    name: str   # the file's path from the project, for reports
    data: Map


@dataclass
class Cable:
    """One cable file."""

    path: Path
    name: str   # the file's path from the project, for reports
    data: Map


@dataclass
class Project:
    root: Path
    config: Map
    car: Map
    boxes: list           # every box file that could be read, as Box
    unread: list          # the box files that could not be read
    cables: list          # every cable file that could be read, as Cable
    unread_cables: list   # the cable files that could not be read
    has_cables: bool      # whether there is a cables/ folder


def load_project(root, report):
    """The whole project, or None when config.yaml or car.yaml cannot be read.

    Box and cable files are read even then, so all their YAML problems are reported.
    """
    root = Path(root)
    config = load(root / "config.yaml", root, report)
    car = load(root / "car.yaml", root, report)
    boxes, unread = load_folder(root, "boxes", Box, report)
    cables, unread_cables = load_folder(root, "cables", Cable, report)
    has_cables = (root / "cables").is_dir()

    if config is None or car is None:
        return None
    return Project(root, config, car, boxes, unread, cables, unread_cables, has_cables)


def load_folder(root, folder, kind, report):
    """Every file of a folder, as `kind` (Box or Cable), and the names of the
    files that could not be read."""
    read = []
    unread = []
    for path in sorted((root / folder).glob("*.yaml")):
        name = path.relative_to(root).as_posix()
        data = load(path, root, report)
        if data is None:
            unread.append(name)
        else:
            read.append(kind(path, name, data))
    return read, unread
