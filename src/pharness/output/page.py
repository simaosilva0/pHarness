"""The pinout as one HTML page: offline, no scripts, the styles inline.

Every value from the project goes through text(), which escapes it.
"""

import re
from html import escape

# Each column's share of the width, the same in every connector's table.
COLUMNS = [
    ("Pin", "5%"),
    ("Net", "11%"),
    ("Type", "9%"),
    ("Wire", "13%"),
    ("To", "15%"),
    ("Cable", "11%"),
    ("Color", "11%"),
    ("At", "12%"),
    ("Note", "13%"),
]
WIRE_COLUMNS = [
    ("From", "24%"),
    ("To", "24%"),
    ("Wire", "18%"),
    ("Type", "14%"),
    ("Color", "20%"),
]

# How each color is drawn in its swatch (CONFIG.md, Colors).
SWATCHES = {
    "black": "#1b1b1b", "brown": "#7b4a26", "red": "#d32f2f", "orange": "#f57c00",
    "yellow": "#fdd835", "green": "#2e7d32", "blue": "#1e63c6", "violet": "#7b3fb5",
    "grey": "#8a8f96", "white": "#ffffff", "pink": "#f48fb1", "turquoise": "#1fb5ad",
    "light blue": "#81c4f5", "dark blue": "#0d2f6e", "light green": "#9ccc65",
    "dark green": "#1b4d1f", "light grey": "#c8ccd1", "beige": "#e8d8b0",
}

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
table.pins { table-layout: fixed; min-width: 60rem; }
table.pins td { overflow-wrap: anywhere; }
.swatch { display: inline-block; width: 0.8em; height: 0.8em; margin-right: 0.35em;
          vertical-align: -0.05em; border: 1px solid var(--muted); border-radius: 2px; }
.picked { font-style: italic; color: var(--muted); }
th, td { text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--head); font-weight: 600; white-space: nowrap; }
tr.unused td { color: var(--unused); }
tr.warned td { background: var(--warn-bg); }
.warning { color: var(--warn-fg); }
section.warnings { margin-top: 1.5rem; padding: 0.6rem 1rem; background: var(--warn-bg); color: var(--warn-fg); }
section.warnings ul { margin: 0.4rem 0 0; padding-left: 1.2rem; }
@media print {
  body { max-width: none; padding: 0; font-size: 11px; }
  section.box, section.cables, section.cable { break-before: page; }
  .connector { break-inside: avoid; }
  a { color: inherit; }
}
"""


def render_page(pinout):
    """The whole page, as text."""
    anchors = section_anchors(pinout)
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
    if pinout.cables:
        parts.append(render_cables(pinout, anchors))
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


# --- the top of the page --------------------------------------------------------

def render_header(pinout):
    counts = (f"{count(len(pinout.boxes), 'box', 'boxes')} · "
              f"{count(pinout.connector_count(), 'connector', 'connectors')} · "
              f"{count(pinout.pin_count(), 'pin', 'pins')}")
    if pinout.cables:
        counts += (f" · {count(len(pinout.cables), 'cable', 'cables')} · "
                   f"{count(pinout.wire_count(), 'wire', 'wires')}")
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
    sections = list(anchors["box"].values()) + list(anchors["cable"].values())
    if anchor(file) in sections:
        return anchor(file)
    return None


def render_index(pinout, anchors):
    rows = []
    for box in pinout.boxes:
        name = f'<a href="#{anchors["box"][box.name]}">{text(box.name)}</a>'
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
    parts = [f'<section class="box" id="{anchors["box"][box.name]}">',
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
        render_cable_link(row.cable, anchors),
    ]
    tds = "".join(f'<td class="mono">{cell}</td>' for cell in code_cells)
    tds += f"<td>{render_color(row.color, row.color_picked)}</td>"
    tds += f'<td class="mono">{text(row.at)}</td>'
    tds += f"<td>{render_note(row)}</td>"
    return f'<tr id="{anchor(row.where)}"{class_attribute}>{tds}</tr>'


def render_to(row, anchors):
    """The far pin links to its row, once a cable says which; otherwise a box
    links to its section; a device is plain text."""
    if row.far is not None:
        return f'<a href="#{anchor(row.far_where)}">{text(row.far)}</a>'
    if row.to_is_box:
        return f'<a href="#{anchors["box"][row.to]}">{text(row.to)}</a>'
    return text(row.to)


def render_cable_link(cable, anchors):
    """A cable links to its section."""
    if cable is None:
        return ""
    if cable in anchors["cable"]:
        return f'<a href="#{anchors["cable"][cable]}">{text(cable)}</a>'
    return text(cable)


def render_color(color, picked):
    """A swatch and the color's name, in italics when the tool picked it."""
    if color is None:
        return ""
    name = text(color)
    if picked:
        name = f'<span class="picked">{name}</span>'
    return f'<span class="swatch" style="background: {swatch(color)}"></span>{name}'


def swatch(color):
    """The swatch's background: the color, or the base with a stripe across."""
    base, _, stripe = str(color).partition("/")
    base_css = SWATCHES.get(base, "transparent")
    if not stripe:
        return base_css
    stripe_css = SWATCHES.get(stripe, "transparent")
    return (f"linear-gradient(135deg, {base_css} 38%, {stripe_css} 38% 62%, "
            f"{base_css} 62%)")


def render_note(row):
    """The note, then each warning on the pin on a line of its own."""
    lines = []
    if row.note:
        lines.append(text(row.note))
    for warning in row.warnings:
        lines.append(f'<span class="warning">{text(warning.rule)}: {text(warning_text(warning))}</span>')
    return "<br>".join(lines)


# --- cables ---------------------------------------------------------------------------

def render_cables(pinout, anchors):
    """The cables: an index, the colors of the types, then every cable's wires."""
    rows = []
    for cable in pinout.cables:
        name = f'<a href="#{anchors["cable"][cable.name]}">{text(cable.name)}</a>'
        ends = text(", ".join(cable.ends))
        rows.append(f"<tr><td>{name}</td><td>{ends}</td><td>{len(cable.wires)}</td>"
                    f"<td>{text(cable.note)}</td></tr>")
    head = "<tr><th>Cable</th><th>Ends</th><th>Wires</th><th>Note</th></tr>"
    parts = ['<section class="cables" id="cables">', "<h2>Cables</h2>",
             f'<div class="scroll"><table>{head}{"".join(rows)}</table></div>',
             render_legend(pinout)]
    parts.append("</section>")
    for cable in pinout.cables:
        parts.append(render_cable(cable, anchors))
    return "\n".join(parts)


def render_legend(pinout):
    """The color of each type's wires; italics where the tool picked it."""
    if not pinout.colors:
        return ""
    rows = "".join(f'<tr><td class="mono">{text(row.type)}{" tap" if row.tap else ""}</td>'
                   f"<td>{render_color(row.color, row.picked)}</td>"
                   f"<td>{'picked by pHarness' if row.picked else 'config.yaml'}</td></tr>"
                   for row in pinout.colors)
    head = "<tr><th>Type</th><th>Color</th><th>From</th></tr>"
    return ("<h3>Colors</h3>"
            '<p class="muted">Colors in italics were picked by the tool; the others are '
            "written in config.yaml, or on the pin or wire.</p>"
            f'<div class="scroll"><table>{head}{rows}</table></div>')


def render_cable(cable, anchors):
    parts = [f'<section class="cable" id="{anchors["cable"][cable.name]}">',
             f"<h2>{text(cable.name)}</h2>"]
    facts = [f"<code>{text(cable.file)}</code>", f"ends: {text(', '.join(cable.ends))}"]
    if cable.part:
        facts.append(f"part: {text(cable.part)}")
    parts.append(f'<div class="muted">{" · ".join(facts)}</div>')
    if cable.note:
        parts.append(f"<p>{text(cable.note)}</p>")

    widths = "".join(f'<col style="width: {width}">' for _, width in WIRE_COLUMNS)
    head = "".join(f"<th>{name}</th>" for name, _ in WIRE_COLUMNS)
    rows = []
    for wire in cable.wires:
        cells = [
            render_wire_end(wire.start, wire.start_where),
            render_wire_end(wire.end, wire.end_where),
            text(wire.wire),
            text(wire.type),
        ]
        tds = "".join(f'<td class="mono">{cell}</td>' for cell in cells)
        tds += f"<td>{render_color(wire.color, wire.color_picked)}</td>"
        rows.append(f"<tr>{tds}</tr>")
    parts.append(f'<div class="scroll"><table class="pins"><colgroup>{widths}</colgroup>'
                 f"<tr>{head}</tr>{''.join(rows)}</table></div>")
    parts.append("</section>")
    return "\n".join(parts)


def render_wire_end(name, where):
    """A pin links to its row; a device is plain text."""
    if where is None:
        return text(name)
    return f'<a href="#{anchor(where)}">{text(name)}</a>'


# --- helpers ------------------------------------------------------------------------

def text(value):
    """A value as escaped text; nothing for a field not written."""
    if value is None:
        return ""
    return escape(str(value))


def anchor(where):
    """An id from a file or file:line: `boxes/nose.yaml:40` -> `boxes-nose-yaml-40`."""
    return re.sub(r"[^A-Za-z0-9]+", "-", where).strip("-")


def section_anchors(pinout):
    """The id of every box's and cable's section, by name, made from its file,
    which is unique: {"box": {name: id}, "cable": {name: id}}. Kept apart, so a
    cable named like a box links to the right one."""
    boxes = {box.name: anchor(box.file) for box in pinout.boxes}
    cables = {cable.name: anchor(cable.file) for cable in pinout.cables}
    return {"box": boxes, "cable": cables}


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
