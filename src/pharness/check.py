"""Running every check on a project, in order. So far, reading its files."""

from .project.load import load_project
from .rules.report import Report


def check_project(root):
    """Read the project at `root` and check it. Returns the Report."""
    report = Report()
    load_project(root, report)
    return report
