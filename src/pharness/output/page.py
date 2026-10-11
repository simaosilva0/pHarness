"""The pinout as one HTML page: offline, no scripts, the styles inline.

Every value from the project goes through text(), which escapes it.
"""

import re
from html import escape

# Each column's share of the width, the same in every connector's table.
COLUMNS = [
    ("Pin", "6%"),
    ("Net", "15%"),
    ("Type", "12%"),
    ("Wire", "17%"),
    ("To", "13%"),
    ("At", "13%"),
    ("Note", "24%"),
]

STYLE = """
:root {
  --bg: #ffffff;
  --fg: #1d1f23;
  --muted: #6a6f78;
  --line: #d9dce1;
  --head: #f3f4f6;
  --link: #1f5fbf;
  --warn-bg: #fff4d6;
  --warn-fg: #7a4b00;
  --unused: #9aa0a8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181c;
    --fg: #e4e6ea;
    --muted: #9aa0a8;
    --line: #33373e;
    --head: #20232a;
    --link: #7fb0ff;
    --warn-bg: #3a2e12;
    --warn-fg: #f2c66b;
    --unused: #6a6f78;
  }
}
body {
  margin: 0 auto;
  max-width: 72rem;
  padding: 1.5rem 1rem 4rem;
  background: var(--bg);
  color: var(--fg);
  font: 15px/1.45 system-ui, sans-serif;
}
h1 { margin: 0 0 0.25rem; font-size: 1.6rem; }
h2 { margin: 2.5rem 0 0.25rem; font-size: 1.3rem; border-bottom: 2px solid var(--line); padding-bottom: 0.25rem; }
h3 { margin: 1.25rem 0 0.4rem; font-size: 1rem; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
code, td.mono { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.9em; }
.muted { color: var(--muted); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
table.pins { table-layout: fixed; min-width: 48rem; }
table.pins td { overflow-wrap: anywhere; }
th, td { text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--head); font-weight: 600; white-space: nowrap; }
tr.unused td { color: var(--unused); }
tr.warned td { background: var(--warn-bg); }
.warning { color: var(--warn-fg); }
section.warnings { margin-top: 1.5rem; padding: 0.6rem 1rem; background: var(--warn-bg); color: var(--warn-fg); }
section.warnings ul { margin: 0.4rem 0 0; padding-left: 1.2rem; }
@media print {
  body { max-width: none; padding: 0; font-size: 11px; }
  section.box { break-before: page; }
  .connector { break-inside: avoid; }
  a { color: inherit; }
}
"""


def render_page(pinout):
    """The whole page, as text."""
    anchors = box_anchors(pinout)
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{text(pinout.car)} pinout</title>",
        f"<style>{STYLE}</style>",
        "</head>",
        "<body>",
        render_header(pinout),
        render_warnings(pinout, anchors),
        render_index(pinout, anchors),
    ]
    for box in pinout.boxes:
        parts.append(render_box(box, anchors))
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


# --- the top of the page --------------------------------------------------------

def render_header(pinout):
    counts = (f"{count(len(pinout.boxes), 'box', 'boxes')} · "
              f"{count(pinout.connector_count(), 'connector', 'connectors')} · "
              f"{count(pinout.pin_count(), 'pin', 'pins')}")
    return (f"<header><h1>{text(pinout.car)} pinout</h1>"
            f'<div class="muted">{counts}</div></header>')


def render_warnings(pinout, anchors):
    """Every warning, each linked to its pin, or to its box when it is on no pin."""
    if not pinout.warnings:
        return ""
    pin_lines = pin_wheres(pinout)
    items = []
    for warning in pinout.warnings:
        label = f"<code>{text(warning.where)}</code> {text(warning.rule)}: {text(warning_text(warning))}"
        target = warning_target(warning, pin_lines, anchors)
        if target is not None:
            label = f'<a href="#{target}">{label}</a>'
        items.append(f"<li>{label}</li>")

    title = count(len(pinout.warnings), "warning", "warnings")
    return (f'<section class="warnings"><strong>{title}</strong>'
            f"<ul>{''.join(items)}</ul></section>")


def warning_target(warning, pin_lines, anchors):
    """Where a warning links to: its pin's row, its box, or nowhere."""
    if warning.where in pin_lines:
        return anchor(warning.where)
    file, _ = warning.file_and_line()
    if anchor(file) in anchors.values():
        return anchor(file)
    return None


def render_index(pinout, anchors):
    rows = []
    for box in pinout.boxes:
        name = f'<a href="#{anchors[box.name]}">{text(box.name)}</a>'
        boards = text(", ".join(box.boards))
        connectors = len(box.connectors)
        pins = box.pin_count()
        rows.append(f"<tr><td>{name}</td><td class=\"mono\">{boards}</td>"
                    f"<td>{connectors}</td><td>{pins}</td></tr>")
    head = "<tr><th>Box</th><th>Boards</th><th>Connectors</th><th>Pins</th></tr>"
    return (f"<nav><h2>Boxes</h2><div class=\"scroll\"><table>{head}{''.join(rows)}"
            "</table></div></nav>")


# --- one box ------------------------------------------------------------------------

def render_box(box, anchors):
    parts = [f'<section class="box" id="{anchors[box.name]}">',
             f"<h2>{text(box.name)}</h2>"]
    facts = [f"<code>{text(box.file)}</code>"]
    if box.boards:
        facts.append(f"boards: <code>{text(', '.join(box.boards))}</code>")
    parts.append(f'<div class="muted">{" · ".join(facts)}</div>')
    if box.note:
        parts.append(f"<p>{text(box.note)}</p>")
    for connector in box.connectors:
        parts.append(render_connector(connector, anchors))
    parts.append("</section>")
    return "\n".join(parts)


def render_connector(connector, anchors):
    title = text(connector.name)
    if connector.part:
        title += f' <span class="muted">({text(connector.part)})</span>'
    parts = ['<div class="connector">', f"<h3>{title}</h3>"]
    if connector.note:
        parts.append(f"<p>{text(connector.note)}</p>")

    widths = "".join(f'<col style="width: {width}">' for _, width in COLUMNS)
    head = "".join(f"<th>{name}</th>" for name, _ in COLUMNS)
    rows = "".join(render_row(row, anchors) for row in connector.rows)
    parts.append(f'<div class="scroll"><table class="pins"><colgroup>{widths}</colgroup>'
                 f"<tr>{head}</tr>{rows}</table></div>")
    parts.append("</div>")
    return "\n".join(parts)


def render_row(row, anchors):
    classes = []
    if row.unused:
        classes.append("unused")
    if row.warnings:
        classes.append("warned")
    class_attribute = ""
    if classes:
        class_attribute = f' class="{" ".join(classes)}"'

    code_cells = [
        text(row.pin),
        text(row.net),
        text(row.type),
        text(row.wire),
        render_to(row, anchors),
        text(row.at),
    ]
    tds = "".join(f'<td class="mono">{cell}</td>' for cell in code_cells)
    tds += f"<td>{render_note(row)}</td>"
    return f'<tr id="{anchor(row.where)}"{class_attribute}>{tds}</tr>'


def render_to(row, anchors):
    """A box links to its section; a device is plain text."""
    if row.to_is_box:
        return f'<a href="#{anchors[row.to]}">{text(row.to)}</a>'
    return text(row.to)


def render_note(row):
    """The note, then each warning on the pin on a line of its own."""
    lines = []
    if row.note:
        lines.append(text(row.note))
    for warning in row.warnings:
        lines.append(f'<span class="warning">{text(warning.rule)}: {text(warning_text(warning))}</span>')
    return "<br>".join(lines)


# --- helpers ------------------------------------------------------------------------

def text(value):
    """A value as escaped text; nothing for a field not written."""
    if value is None:
        return ""
    return escape(str(value))


def anchor(where):
    """An id from a file or file:line: `boxes/nose.yaml:40` -> `boxes-nose-yaml-40`."""
    return re.sub(r"[^A-Za-z0-9]+", "-", where).strip("-")


def box_anchors(pinout):
    """Box name -> its section's id, made from its file, which is unique."""
    anchors = {}
    for box in pinout.boxes:
        anchors[box.name] = anchor(box.file)
    return anchors


def pin_wheres(pinout):
    """The file:line of every pin on the page."""
    wheres = set()
    for box in pinout.boxes:
        for connector in box.connectors:
            for row in connector.rows:
                wheres.add(row.where)
    return wheres


def warning_text(warning):
    """What is wrong, with the entry as `accept` names it, so it can be copied."""
    if warning.entry:
        return f"{warning.entry}: {warning.what}"
    return warning.what


def count(n, one, many):
    """`1 box`, `2 boxes`."""
    if n == 1:
        return f"1 {one}"
    return f"{n} {many}"
