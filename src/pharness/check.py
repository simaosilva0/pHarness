"""Running every check on a project, in order: the files, config.yaml, then
the model built from them."""

from .checks.boxes import check_boxes
from .checks.car import check_car
from .checks.config import check_config
from .checks.names import NetChecks
from .project.load import load_project
from .project.read import read_model
from .rules.report import Report


def check_project(root):
    """Read the project at `root` and check it. Returns the Report."""
    report = Report()
    project = load_project(root, report)
    if project is None:
        return report

    settings = check_config(project.config, report)
    model = read_model(project, settings, report)
    nets = NetChecks(model, report)

    check_car(model, nets, report)
    check_boxes(model, nets, report)
    return report
