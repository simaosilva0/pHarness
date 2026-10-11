"""config.yaml: styles, sides, types, rule levels and accepted entries
(CONFIG.md: Styles, Types, Rule levels)."""

import re

from ..project.fields import check_fields, get_list, get_map, is_map, where
from ..project.settings import KINDS, KINDS_WITHOUT_WORDS, RESERVED, Kind, Settings
from ..project.styles import DEFAULT_STYLE, NET_STYLES, STYLES, is_net_word
from ..rules.rules import LEVELS, RULES

FILE = "config.yaml"
CONFIG_FIELDS = ["style", "sides", "types", "rules", "accept"]
KIND_FIELDS = ["types", "label", "qualifiers"]


def check_config(config, report):
    """Every rule on config.yaml. Also sets the rule levels and accepted entries
    on the report, so call it before any other check."""
    check_fields(config, CONFIG_FIELDS, FILE, "config", report)
    check_all_there(config, CONFIG_FIELDS, FILE, config.line, "config", report)
    read_rule_levels(config, report)
    read_accepted(config, report)

    style = check_styles(config, report)
    sides = get_list(config, "sides", FILE, report)
    kinds = read_kinds(config, report)

    check_net_words(sides, kinds, style["net"], config, report)
    check_type_words(kinds, report)
    return Settings(style, sides, kinds)


# --- everything written -------------------------------------------------------

def check_all_there(m, names, file, line, what, report):
    """config-fields: config.yaml writes every setting, defaults included, so
    the file shows everything a project can change. Returns what is missing."""
    missing = [name for name in names if name not in m]
    report.check("config-fields", not missing, f"{file}:{line}", f"{what}: no {', '.join(missing)}")
    return missing


def check_section_lists_all(config, section, names, report):
    """config-fields on a section that lists every kind of name, kind or rule.
    A missing section is reported once, on config.yaml itself. Returns what is
    missing from the section."""
    if section not in config:
        return list(names)
    m = get_map(config, section, FILE, report)
    return check_all_there(m, names, FILE, config.at[section], section, report)


# --- styles ------------------------------------------------------------------

def check_styles(config, report):
    """style-kind, style-name, style-net, and every kind of name listed.
    Returns the style of every kind of name: None when it is set wrong or left
    out, so the names of that kind are not checked against a style nobody chose."""
    style = dict(DEFAULT_STYLE)
    for kind in check_section_lists_all(config, "style", DEFAULT_STYLE, report):
        style[kind] = None
    given = get_map(config, "style", FILE, report)

    for kind, name in given.items():
        at = where(FILE, given, kind)
        kind_known = report.check("style-kind", kind in DEFAULT_STYLE, at,
                                  f"{kind} is not a kind of name")
        name_known = report.check("style-name", isinstance(name, str) and name in STYLES, at,
                                  f"{kind}: there is no style {name}")
        if kind == "net" and name_known:
            name_known = report.check("style-net", name in NET_STYLES, at,
                                      f"net: {name} has no separator for sides and indexes")
        if not kind_known:
            continue
        if name_known:
            style[kind] = name
        else:
            style[kind] = None

    return style


def check_net_words(sides, kinds, net_style, config, report):
    """net-words-case: sides, labels and qualifiers end up in nets and wire
    labels, so each is one word in the nets' case."""
    if net_style is None:
        return
    for side in sides:
        report.check("net-words-case", is_net_word(side, net_style), where(FILE, config, "sides"),
                     f"side {side} is not one {net_style} word")

    for kind in kinds.values():
        at = f"{FILE}:{kind.line}"
        if kind.label is not None:
            report.check("net-words-case", is_net_word(kind.label, net_style), at,
                         f"{kind.name} label {kind.label} is not one {net_style} word")
        for qualifier in kind.qualifiers:
            report.check("net-words-case", is_net_word(qualifier, net_style), at,
                         f"{kind.name} qualifier {qualifier} is not one {net_style} word")


# --- types -------------------------------------------------------------------

def read_kinds(config, report):
    """type-kinds and kind-form on every kind under `types`, and every kind
    listed. Returns them as Kinds."""
    kinds = {}
    check_section_lists_all(config, "types", KINDS, report)
    types = get_map(config, "types", FILE, report)

    for name, entry in types.items():
        at = where(FILE, types, name)
        if not is_map(entry, FILE, types.at[name], f"kind {name}", report):
            continue
        check_fields(entry, KIND_FIELDS, FILE, f"kind {name}", report)
        check_all_there(entry, ["types"], FILE, types.at[name], f"kind {name}", report)
        report.check("type-kinds", name in KINDS, at, f"{name} is not a kind")

        words = get_list(entry, "types", FILE, report)
        label = entry.get("label")
        qualifiers = [str(q) for q in get_list(entry, "qualifiers", FILE, report)]
        well_formed = check_kind_form(name, entry, words, at, report)
        kinds[name] = Kind(name, words, label, qualifiers, types.at[name], well_formed)

    return kinds


def check_kind_form(name, entry, words, at, report):
    """kind-form: a label or qualifiers, not both; chain and no_net neither; a
    kind the project does not use is `{types: []}` alone. Returns whether it passed."""
    has_label = "label" in entry
    has_qualifiers = "qualifiers" in entry

    if "types" not in entry:
        return False   # config-fields says so; whether it is used is not known
    if not words:
        ok = not has_label and not has_qualifiers
        what = f"{name} is not used, so it is {{types: []}} alone"
    elif name in KINDS_WITHOUT_WORDS:
        ok = not has_label and not has_qualifiers
        what = f"{name} takes neither a label nor qualifiers"
    else:
        ok = has_label != has_qualifiers
        what = f"{name} takes a label or qualifiers, exactly one of them"
    return report.check("kind-form", ok, at, what)


def check_type_words(kinds, report):
    """type-word-case, type-word-twice, type-reserved."""
    kinds_of_word = {}   # type word -> the kinds it is in
    for kind in kinds.values():
        for word in kind.words:
            at = f"{FILE}:{kind.line}"
            is_lower = isinstance(word, str) and re.fullmatch(r"[a-z0-9]+", word) is not None
            report.check("type-word-case", is_lower, at, f"type {word} is not lower case letters and digits")
            kinds_of_word.setdefault(word, []).append(kind)

    for word, in_kinds in kinds_of_word.items():
        at = f"{FILE}:{in_kinds[0].line}"
        names = [kind.name for kind in in_kinds]
        if len(in_kinds) > 1:
            report.check("type-word-twice", may_be_in_both(word, in_kinds), at,
                         f"type {word} is in {', '.join(names)}")
        if word in RESERVED:
            for name in names:
                report.check("type-reserved", name in RESERVED[word], at,
                             f"type {word} is in {name}; it belongs in {' or '.join(RESERVED[word])}")


def may_be_in_both(word, in_kinds):
    """A word is in two kinds only when exactly one has qualifiers, or it is
    hv in pair and phase."""
    names = sorted(kind.name for kind in in_kinds)
    if word == "hv" and names == ["pair", "phase"]:
        return True
    with_qualifiers = [kind for kind in in_kinds if kind.qualifiers]
    return len(in_kinds) == 2 and len(with_qualifiers) == 1


# --- rule levels and accepted entries -----------------------------------------

def read_rule_levels(config, report):
    """rule-known, rule-fixed, rule-level on `rules`, and every adjustable rule
    listed. Sets the levels on the report; a rule left out keeps its default."""
    check_section_lists_all(config, "rules", adjustable_rules(), report)
    levels = get_map(config, "rules", FILE, report)
    for rule, level in levels.items():
        at = where(FILE, levels, rule)
        if not is_adjustable_rule(rule, at, report):
            continue
        if report.check("rule-level", level in LEVELS, at, f"{rule}: there is no level {level}"):
            report.levels[rule] = level


def read_accepted(config, report):
    """rule-known, rule-fixed, accept-reason on `accept`. Sets the accepted
    entries on the report; whether each exists is checked once the project is read."""
    accept = get_map(config, "accept", FILE, report)
    for rule in accept:
        if not is_adjustable_rule(rule, where(FILE, accept, rule), report):
            continue
        entries = get_map(accept, rule, FILE, report)
        report.accepted[rule] = {}
        for entry, reason in entries.items():
            at = where(FILE, entries, entry)
            has_reason = isinstance(reason, str) and reason.strip() != ""
            report.check("accept-reason", has_reason, at, f"{rule}: {entry} has no reason")
            report.accepted[rule][str(entry)] = at


def adjustable_rules():
    return [rule for rule in RULES if RULES[rule].adjustable]


def is_adjustable_rule(rule, at, report):
    """rule-known and rule-fixed, on a rule named under `rules` or `accept`."""
    if not report.check("rule-known", rule in RULES, at, f"there is no rule {rule}"):
        return False
    return report.check("rule-fixed", RULES[rule].adjustable, at, f"{rule} is fixed")
