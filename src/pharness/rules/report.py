"""Collecting problems, with the levels and accepted entries of config.yaml."""

from collections import Counter
from dataclasses import dataclass

from .rules import RULES


@dataclass
class Problem:
    """One broken rule on one entry."""

    rule: str
    level: str                 # "error" or "warn"
    where: str                 # "file:line", or the file alone
    what: str                  # what is wrong
    entry: str | None = None   # the entry as `accept` names it, on adjustable rules

    def file_and_line(self):
        file, _, line = self.where.partition(":")
        if line.isdigit():
            return file, int(line)
        return file, 0

    def __str__(self):
        text = self.what
        if self.entry:
            text = f"{self.entry}: {text}"
        return f"{self.where}: {self.level} {self.rule}: {text}"


class Report:
    """Every check goes through check(), which applies the levels and `accept`."""

    def __init__(self):
        self.problems = []
        self.levels = {}           # rule -> level, the changes under `rules`
        self.accepted = {}         # rule -> {entry: where}, under `accept`
        self.accept_hits = set()   # (rule, entry): it broke, and was accepted
        self.skipped = set()       # (rule, entry): not checked, because of another mistake
        self.ran = Counter()       # rule -> how many times it was checked

    def level(self, rule):
        if rule in self.levels:
            return self.levels[rule]
        return RULES[rule].level

    def is_accepted(self, rule, entry):
        return entry in self.accepted.get(rule, {})

    def check(self, rule, ok, where, what, entry=None):
        """Check one rule on one entry and remember it if it broke.

        Returns whether it passed, so a caller can skip the checks that only
        make sense when this one passed.
        """
        level = self.level(rule)
        if level == "off":
            return True

        self.ran[rule] += 1
        if ok:
            return True

        if self.is_accepted(rule, entry):
            self.accept_hits.add((rule, entry))
            return True

        self.problems.append(Problem(rule, level, where, what, entry))
        return False

    def skip(self, rule, entry):
        """Remember that a rule was not checked on an entry because another
        mistake is in the way, so `accept` cannot call the entry stale."""
        self.skipped.add((rule, entry))

    def errors(self):
        return [p for p in self.problems if p.level == "error"]

    def warnings(self):
        return [p for p in self.problems if p.level == "warn"]

    def sorted_problems(self):
        """Errors first, then warnings, each in file and line order."""
        def order(problem):
            file, line = problem.file_and_line()
            is_warning = problem.level == "warn"
            return (is_warning, file_order(file), file, line)

        return sorted(self.problems, key=order)

    def summary(self):
        errors = count(len(self.errors()), "error")
        warnings = count(len(self.warnings()), "warning")
        return f"{errors}, {warnings}"


def file_order(file):
    """The order files are read in: config.yaml, car.yaml, then the rest."""
    if file == "config.yaml":
        return 0
    if file == "car.yaml":
        return 1
    return 2


def count(n, word):
    """`1 error`, `2 errors`."""
    if n == 1:
        return f"1 {word}"
    return f"{n} {word}s"
