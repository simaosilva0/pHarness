"""The command line: `pharness check [project]`, `pharness build [project]`."""

import argparse
from pathlib import Path

from .check import check_project, read_and_check
from .output.page import render_page
from .output.pinout import build_pinout

DEFAULT_OUTPUT = Path("build") / "pinout.html"   # inside the project


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pharness", description="Wiring harness concepts in YAML, checked.")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check a project and print every problem")
    check.add_argument("project", nargs="?", default=".", help="the project folder (default: here)")

    build = commands.add_parser("build", help="check a project and write its pinout page")
    build.add_argument("project", nargs="?", default=".", help="the project folder (default: here)")
    build.add_argument("-o", "--output", help="the page to write (default: <project>/build/pinout.html)")

    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args.project)
    if args.command == "build":
        return run_build(args.project, args.output)
    return 2


def run_check(project):
    """Print every problem and a summary. Exits 1 when there is an error."""
    report = check_project(project)
    print_report(report)

    if report.errors():
        return 1
    return 0


def run_build(project, output):
    """Check the project and write its pinout page. With an error, print the
    problems and write nothing."""
    report, model = read_and_check(project)
    print_report(report)
    if report.errors():
        print("nothing written: fix the errors first")
        return 1

    if output is None:
        output = Path(project) / DEFAULT_OUTPUT
    output = Path(output)

    page = render_page(build_pinout(model, report))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    print(f"wrote {output}")
    return 0


def print_report(report):
    for problem in report.sorted_problems():
        print(problem)
    print(report.summary())
