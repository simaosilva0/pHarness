# Structure

The files of a project and every field in them. Names and types inside them
follow `CONFIG.md`.

## Files

```
<project>/
  config.yaml          styles, sides, types, rule levels, accepted entries (CONFIG.md)
  car.yaml             the car: devices, buses, links, chains
  boxes/<box>.yaml     one file per box: its connectors and their pins
  cables/<cable>.yaml  one file per cable: its wires (optional)
```

Every file is plain YAML, read as YAML 1.2: only `true` and `false` are
booleans, so `off`, `no` and `on` stay words. A key written twice is an error, every name is
matched exactly, and every problem is reported with its file and line. A field
not listed here is an error, so a typo in a field name never goes unnoticed.

The rules are in tables like those in `CONFIG.md`, with the same columns.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `yaml` | `config.yaml` and `car.yaml` are there, and every file is valid YAML and a mapping of fields | | a tab used for indenting, a box file that is a list | error | |
| `key-once` | no key is written twice in the same mapping | | connector `APPS1` twice in one box | error | |
| `field-known` | every field is one listed here | `note` | `notes` | error | |
| `field-shape` | every field holds what its table says: a mapping, a list, text or a number | `sides: [LEFT, RIGHT]` | `sides: LEFT` | error | |

A project can start with boxes only. Without cables, pins are joined by net and
type: every pin with the same net and the same type is one conductor. Cables
add the actual wires once they are known.

## `car.yaml`

```yaml
car: FST 11

devices:
  APPS1: {note: accelerator pedal sensor 1}
  Side Panel: {}
  MH L ASSI: {note: main hoop left ASSI lamp}

buses:
  CAN_E: {bitrate: 1000000, ends: [PDU Box, ACU Box, Rear Box, AS, Inverters]}
  CAN_AMK: {bitrate: 1000000, ends: [Inverters], internal: true}

links:
  ETH_CAMERA: {ends: [Ethernet Switch, Camera]}

chains:
  SDC:
    - {node: LVMS, out: D0}
    - {node: ASMS, out: D1}
    - {node: RES, out: D2, box: RES}
```

| field | | |
|---|---|---|
| `car` | required | the car's name |
| `devices` | optional | every part that is not a box but has pins wired to it: sensors, switches, lamps, motors. A device is where wires end: anything they pass through is a box, even with nothing inside (a bulkhead, a charge port). Keyed by name (device rule in `CONFIG.md`), each with an optional `note` |
| `buses` | optional | CAN, LIN, RS-485, I2C and SPI buses, keyed by name (`<KIND>_<BUS>`, `CONFIG.md`). `bitrate`, and `data_bitrate` for CAN FD, its `ends` (the boxes it lands in and the devices on it, not the boxes it only passes through), `internal: true` when it never leaves its box |
| `links` | optional | Ethernet links, keyed by name (`ETH_<LINK>`), with their `ends` (boxes or devices) |
| `chains` | optional | series loops in the order current flows (`CONFIG.md`). Each node has a `node` name (in the device style; inside a box, the part it is), an `out` label and, when the node is inside a box, that `box`; a node outside every box is a device |

The boxes of the car are the files in `boxes/`; they are not listed again.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `car-name` | `car` is there | `car: FST 11` | no `car` | error | |
| `bus-fields` | every bus has `bitrate` and `ends`, every link has `ends`, `data_bitrate` is only on a CAN bus, both are whole numbers above 0, `internal` is only ever `true` | `{bitrate: 1000000, ends: [AS, RES]}` | `{ends: [AS, RES]}` | error | |
| `chain-fields` | every chain node has `node` and `out` | `{node: RES, out: D2, box: RES}` | `{node: RES, box: RES}` | error | |
| `ends-known` | every end of a bus or link is a box or a device | `ends: [Front Box, STA]` | `ends: [Front box]` | error | |
| `ends-match` | the ends of a bus or link are exactly the boxes it lands in (a pin on it that is not `pass`) and the devices a pin on it goes `to`. A box it only passes through is not an end. An `internal` bus never reaches a connector, so it is not checked | `CAN_BAT` ends `[Accumulator, Front Box]`, both with `CAN_BAT` pins | `SW` in the ends of `CAN_S` with no `CAN_S` pin in `SW` | error | yes |
| `bus-internal` | a bus is `internal` exactly when it has one end and that end is a box | `CAN_AMK` with `ends: [Inverters]` | `internal: true` with two ends | error | yes |
| `device-used` | every device is a `to`, an end or a chain node | `APPS1` | a device nothing points at | warn | yes |

## `boxes/<box>.yaml`

```yaml
box: Pedal Box
boards: [te]
note: under the pedals, the TE board inside

connectors:
  APPS1:
    part: AS010-35SB
    note: to the accelerator pedal sensor
    pins:
      - {pin: '1', net: APPS1, type: ground, to: APPS1}
      - {pin: '2', net: APPS1, type: power:5V, to: APPS1}
      - {pin: '3', net: APPS1, type: analog, to: APPS1, at: te:RB0}
      - {pin: '4', type: spare}
```

The file is named after the box, lower case, with every character that is not
a letter or digit as `_` (`Pedal Box` is `pedal_box.yaml`). Two boxes may not
share a file name.

Box:

| field | | |
|---|---|---|
| `box` | required | the box's name |
| `boards` | with `at` pins | the boards inside, named after their firmware, in the board style (`te`, `suspot-front`); what `at` points to. Lists every board in the box; required as soon as a pin in the box has an `at`, and every `at` names one of them |
| `note` | optional | free text |
| `connectors` | required | keyed by connector name, unique in the box |

Connector:

| field | | |
|---|---|---|
| `part` | optional | the part number |
| `note` | optional | free text |
| `pins` | required | in the order they are printed |

Pin:

| field | | |
|---|---|---|
| `pin` | required | as printed on the connector, always a string (`'1'`, `a`) |
| `net` | with a net | the net (`CONFIG.md`); left out on `spare` and `unfitted` pins |
| `type` | required | the type (`CONFIG.md`) |
| `to` | optional | where the wire leaving this pin ends: the next box, or the device when it plugs straight in; a box or a device in `car.yaml`. A wire through several boxes is one `to` per hop, and following them gives the whole route |
| `at` | optional | where the pin lands inside the box: `<board>:<pin>`, always with the board, even when the box has only one (`te:RB0`, `acu:RB14`); or `pass` when it only passes through to another connector of the box |
| `note` | optional | free text; on an `unfitted` pin, what it was for |

The tool writes one pin per line, the fields always in the order above and
nothing lined up, so a hand edit never forces realigning its neighbours. A
value YAML would read differently is quoted: a pin of digits (`'1'`), a note
with a comma or a colon:

```yaml
      - {pin: '1', net: PEDAL_BOX, type: shield}
      - {pin: '2', net: TE, type: power:24V, to: Front Box}
      - {pin: '11', type: spare}
      - {pin: '12', type: unfitted, note: 'TITS, dropped before fitting'}
```

Inside a box, pins with the same net and type are joined: a supply that comes in
on one connector and leaves on another is one conductor without a wire.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `box-file` | the file is named after its box | `pedal_box.yaml` for `Pedal Box` | `pedal-box.yaml` | error | |
| `box-fields` | `box` and `connectors` are there, and `boards` when any pin has an `at` | `box: Pedal Box`, `boards: [te]` | an `at: te:RB0` in a box with no `boards` | error | |
| `connector-pins` | every connector has `pins` | | a connector with only a `part` | error | |
| `pin-fields` | every pin has `pin` and `type` | `{pin: '4', type: spare}` | `{pin: '4'}` | error | |
| `pin-string` | `pin` is a string | `'1'`, `a` | `1` | error | |
| `pin-net` | a pin has a `net` unless its type is `spare` or `unfitted`, which never have one | `{pin: '4', type: spare}` | `{pin: '4', net: TE, type: spare}`, `{pin: '3', type: analog}` | error | |
| `to-known` | `to` is a box or a device | `to: Front Box`, `to: APPS1` | `to: Front box` | error | |
| `to-reaches` | when `to` is a box, that box has a pin with the same net and type | `ACC` `power:24V` `to: PDU Box`, and `PDU Box` has an `ACC` `power:24V` pin | `to: Front Box` with no matching pin in `Front Box` | error | yes |
| `at-form` | `at` is `pass`, or `<board>:<pin>` with a board in `boards` | `te:RB0`, `pass` | `RB0`, `pdu:RB0` in a box without `pdu` | error | |
| `at-pass` | a `pass` pin has a pin with the same net and type on another connector of its box | | `pass` with nothing to pass to | error | yes |
| `pin-order` | the fields are in the order `pin`, `net`, `type`, `to`, `at`, `note` | `{pin: '1', net: TE, type: ground}` | `{type: ground, pin: '1', net: TE}` | warn | yes |

## `cables/<cable>.yaml`

Shape only; the details are decided with step 9. A cable says which connectors
it joins; most of that is already in the `to`s, so cables add only what boxes
cannot say: a stretch from one device straight to another (LVMS to ASMS on the
SDC), and which wires run together.

```yaml
cable: Pedal Box Splitter
ends: [Pedal Box.Splitter, Splitter Box.In]
wires: by-net
```

| field | | |
|---|---|---|
| `cable` | required | the cable's name, same rule as a box |
| `ends` | required | what it joins: connectors as `<box>.<connector>`, or devices |
| `wires` | required | `by-net`: one wire between every pair of pins on the two ends with the same net and type. Or a list of wires, each `{from: <box>.<connector>.<pin>, to: ..., color: ...}`, for anything else |
| `splices` | optional | where one conductor splits inside the cable |

Every wire has a color, set by the project in `config.yaml`, one per type:

```yaml
color: fill
colors:
  ground: black
  power:24V: red
  can:H: yellow
  can:L: green
```

| `color` | the project writes | a type with no color |
|---|---|---|
| `auto` (left out) | no `colors` | gets its kind's color: every supply one color, every ground another |
| `fill` | some `colors` | gets its kind's color |
| `strict` | every type in use | is an error |

A wire's own `color` in a cable's list overrides its type's. The drawings'
legend marks the colors the tool picked, so a chosen red and a picked red are
never confused.

Left to RapidHarness, after the concept phase: wire gauge, length, twisting
(a pair type already says it), current, and the pins on a device's own
connector.

No rules yet: they come with step 9.

## Not part of the structure

The SIL keeps its own files next to these (`plant.yaml`, `modules/`). They
refer to conductors by their wire label (`APPS1_SIG`, `CONFIG.md`), which the
tool can print for every pin.

## Decided

- `to`, not the SIL's `peer`. It is the far end of the wire, never the last
  consumer behind other boxes: the route is the chain of `to`s.
- Devices are declared in `car.yaml`, so a misspelled `to` is an error.
- `at` is a board pin or `pass`; the SIL's `device`, `electronics` and
  `hardwired` are dropped, since `to` says it.
- No CAN `dir` and no connector `kind` for now: bus topology comes with cables,
  and the part number gives the family.
- Buses and links list their `ends`: the boxes they land in and the devices,
  never a box they only pass through.
- `part` is optional.
