"""Every test works on its own copy of Kestrel, the made-up test car, plants
one mistake in it and checks which rules broke."""

import shutil
from pathlib import Path

import pytest

from pharness.check import check_project

KESTREL = Path(__file__).parent / "kestrel"


class Project:
    """A copy of Kestrel to plant mistakes in."""

    def __init__(self, root):
        self.root = root

    def replace(self, file, old, new):
        """Replace the one place `old` is written in a file."""
        path = self.root / file
        text = path.read_text()
        assert text.count(old) == 1, f"{old!r} is not written exactly once in {file}"
        path.write_text(text.replace(old, new))

    def add(self, file, text):
        """Add lines at the end of a file."""
        path = self.root / file
        path.write_text(path.read_text() + text)

    def write(self, file, text):
        path = self.root / file
        path.write_text(text)

    def remove(self, file):
        (self.root / file).unlink()

    def check(self):
        return check_project(self.root)

    def broken(self):
        """The rules that broke, each with where: [(rule, "file:line")]."""
        report = self.check()
        return [(p.rule, p.where) for p in report.sorted_problems()]

    def broken_rules(self):
        """The rules that broke, each once, sorted."""
        return sorted({rule for rule, _ in self.broken()})


@pytest.fixture
def project(tmp_path):
    """A fresh copy of Kestrel for one test."""
    root = tmp_path / "kestrel"
    shutil.copytree(KESTREL, root)
    return Project(root)
