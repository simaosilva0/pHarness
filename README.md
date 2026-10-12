# pHarness

Wiring harness concepts in YAML, checked.

pHarness is a small tool for the concept phase of a vehicle wiring harness. The
boxes, connectors, pins, cables, buses and series loops (like a shutdown circuit)
are written as plain YAML files. The tool checks them against a strict set of
naming and structure rules and turns them into pinout tables and a wire list for
every cable.

It was made for Formula Student-sized cars: a few boxes, a few hundred pins, and a
team that has to agree on what goes where before anyone crimps a wire. After the
concept phase the harness moves to a full harness tool (wire gauges, lengths,
manufacturing drawings). pHarness doesn't try to replace that tool.

## Why

A harness that lives in spreadsheets and schematics drifts. The same wire gets
a different spelling on each end (`24V_1` on one side, `24V(1)` on the other), a
pin points at a box that has no pin for it, a CAN bus lists a box it never
reaches. pHarness makes those mistakes visible:

- **A name is right or it is wrong.** Names are matched exactly. `CAN_E` and
  `can_e` are two different nets, and the one that breaks the project's style
  is reported. There are no aliases and no fuzzy matching.
- **Every problem has a file and a line.** You fix the YAML where it's written.
- **The rules are written down.** [`CONFIG.md`](CONFIG.md) covers how nets, types,
  boxes, connectors and devices are named. [`STRUCT.md`](STRUCT.md) covers the
  files and every field in them. Each section ends with a table of the rules the
  tool checks.

## A project

```
my-car/
  config.yaml          styles, sides, types, colors, rule levels, accepted entries
  car.yaml             the car: devices, buses, Ethernet links, chains
  boxes/<box>.yaml     one file per box: its connectors and their pins
  cables/<cable>.yaml  one file per cable: what it joins (optional)
```

A pin says which **net** it belongs to and what **type** of conductor it is.
Pins with the same net and type are the same conductor. `to` is the far end of
the wire leaving the pin, and `at` is where the pin lands inside the box:

```yaml
box: Nose
boards: [front_io]

connectors:
  pedals:
    part: DT06-12S
    pins:
      - {pin: '1', net: apps1, type: ground, to: APPS1}
      - {pin: '2', net: apps1, type: power:5v, to: APPS1}
      - {pin: '3', net: apps1, type: analog, to: APPS1, at: front_io:a0}
      - {pin: '10', type: spare}
```

A cable file only says what the cable joins. Which cable each wire runs in is
written once, on the connector, or on the pin when a connector takes more than
one cable:

```yaml
cable: Pedals
ends: [Nose.pedals, APPS1, APPS2, BPPS]
```

```yaml
  pedals:
    part: DT06-12S
    cable: Pedals
    pins:
      - {pin: '1', net: apps1, type: ground, to: APPS1}
```

The tool works out every wire from that: a pin going to a device is a wire to
it, and a pin going to a box is a wire to the one pin there with the same net
and type on the same cable. A project can leave `cables/` out until the wires
are known.

Buses, Ethernet links and series loops are listed in `car.yaml`:

```yaml
car: Kestrel

buses:
  can_chassis: {bitrate: 500000, ends: [Nose, Cockpit, RearHub, IMU]}

chains:
  sdc:
    - {node: Left Shutdown Button, out: s0}
    - {node: BSPD, out: s5, box: RearHub}
```

[`example/`](example) is a complete made-up car (7 boxes, 216 pins, 28 cables,
CAN FD, LIN, RS-485, I2C, SPI, Ethernet and two chains). Use it as a reference.

## Install

Python 3.10 or newer. PyYAML is the only dependency.

```sh
git clone git@github.com:simaosilva0/pHarness.git
cd pHarness
pip install -e .
```

## Run

Check a project and print every problem:

```sh
pharness check example
```

Kestrel passes with `0 errors, 0 warnings`. Here is the output for a copy with
two planted mistakes:

```
boxes/nose.yaml:11: error net-style: net Apps1 is not snake
boxes/nose.yaml:43: warn conductor-one-end: horn digital: horn digital is on one pin, not going to a device
1 error, 1 warning
```

It exits with 1 when there is an error, so it can run in CI.

Build the pinout page, an offline HTML file with every box, connector and pin,
the wire label, cable and color of each wire, a wire list for every cable, and a
diagram of the whole car (the Car tab: zoom and pan, move boxes, devices and
cables on a grid, filter, search, save as SVG or PNG, light or dark):

```sh
pharness build example             # writes example/build/pinout.html
pharness build example -o out.html
```

If the project has an error, `build` writes nothing. Warnings still let it build,
and the page lists them.

## Wire colors

Every wire gets a color. `config.yaml` says which colors the project may use and
where they come from:

```yaml
palette: striped   # solid, striped (the default) or shaded
color: fill        # auto, fill or strict
colors:
  ground: black
  can:l: green
```

`palette` is the set of names: the twelve IEC 60757 colors (`solid`), those and
any two as `base/stripe` (`striped`, the industry standard), or those and light
and dark shades (`shaded`). Under `auto` the tool picks every color, under
`fill` it picks the ones the project left out, and under `strict` every type
needs one. A picked color is the kind's base color, then the base with a
stripe, so each type gets its own: supply is red, then red/white. High voltage
is always orange, and nothing else is. The page marks which colors were picked.

## Rule levels

Some rules are about completeness, and a concept harness may not meet them yet.
A wire nobody has traced to its far end is one example. A device no pin reaches
is another. Those rules are adjustable in `config.yaml` (`error`, `warn` or
`off`). A single known exception can be accepted, with its reason, without
turning the rule off:

```yaml
rules:
  conductor-one-end: warn
  pin-order: off

accept:
  to-reaches:
    Accumulator.Data.11: the far end pin is not known yet
```

The naming grammar and the file structure are fixed.

## Tests

```sh
pip install pytest
pytest
```

Each test copies Kestrel, plants one mistake, and checks that the expected rule
broke at the expected line.

## Code layout

```
src/pharness/
  cli.py, check.py   the command line, and running every check in order
  project/           reading the files into a model, with lines on everything;
                     wire labels and colors
  rules/             the list of rules, their levels, the report
  checks/            the checks: config, names, car, boxes, routes, cables,
                     colors, accept
  output/            pinout tables, cable wire lists and the HTML page
```

## Status and what's next

Done: the naming rules, the file structure, the loader and every check in the
two documents, cables and wire colors, and the pinout page.

Next, roughly in order:

- **Buses and chains** checked along the cables, including the order of a series
  loop, and a color of its own for a wire that only taps a chain.
- **Drawings**: a block diagram of the boxes, with buses as rails.
- **`pharness init`**: a new project with a complete default `config.yaml`.
- **Stock cables**: a bought multicore as a template, with its cores' colors.
- CI.

Out of scope: wire gauge, length, current and manufacturing detail. Those belong
in the harness tool used after the concept phase.

## License

MIT
