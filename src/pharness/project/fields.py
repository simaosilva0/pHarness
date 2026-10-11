"""Reading the fields of a mapping safely (STRUCT.md, Files).

Every check reads fields through these, so a field nobody knows and a field of
the wrong shape are reported the same way everywhere, and a wrong shape never
crashes the checks after it: they see an empty value instead.
"""

from .load import Map


def where(file, m, key=None):
    """`file:line` of a mapping, or of one of its keys."""
    if key is not None and key in m.at:
        return f"{file}:{m.at[key]}"
    return f"{file}:{m.line}"


def check_fields(m, allowed, file, what, report):
    """field-known: every key of the mapping is one of `allowed`."""
    for key in m:
        known = key in allowed
        report.check("field-known", known, where(file, m, key), f"{what}: unknown field {key}")


def get_map(m, key, file, report):
    """The mapping under `key`, or an empty one when it is missing or not a mapping."""
    value = m.get(key)
    if value is None:
        return Map(m.line)
    if not report.check("field-shape", isinstance(value, Map), where(file, m, key),
                        f"{key} is not a mapping"):
        return Map(m.line)
    return value


def get_list(m, key, file, report):
    """The list under `key`, or an empty one when it is missing or not a list."""
    value = m.get(key)
    if value is None:
        return []
    if not report.check("field-shape", isinstance(value, list), where(file, m, key),
                        f"{key} is not a list"):
        return []
    return value


def is_map(value, file, line, what, report):
    """field-shape on a value that is not under a key, such as an item of a list."""
    return report.check("field-shape", isinstance(value, Map), f"{file}:{line}", f"{what} is not a mapping")


def is_text_name(name, file, line, what, report):
    """field-shape on a name written as a key: devices, buses, connectors... are
    named with text, so `1:` is reported and left out."""
    return report.check("field-shape", isinstance(name, str), f"{file}:{line}", f"{what} {name} is not text")
