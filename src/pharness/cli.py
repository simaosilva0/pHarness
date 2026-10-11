"""The command line: `pharness check [project]`."""

import argparse

from .check import check_project


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pharness", description="Wiring harness concepts in YAML, checked.")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check a project and print every problem")
    check.add_argument("project", nargs="?", default=".", help="the project folder (default: here)")

    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args.project)
    return 2


def run_check(project):
    """Print every problem and a summary. Exits 1 when there is an error."""
    report = check_project(project)
    print_report(report)

    if report.errors():
        return 1
    return 0


def print_report(report):
    for problem in report.sorted_problems():
        print(problem)
    print(report.summary())
