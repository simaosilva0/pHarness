# Structure

The files of a project and every field in them. Names and types inside them
follow `CONFIG.md`.

## Files

```
<project>/
  config.yaml          styles, sides, types, rule levels, accepted entries (CONFIG.md)
  car.yaml             the car: devices, buses, links, chains
  boxes/<box>.yaml     one file per box: its connectors and their pins
  cables/<cable>.yaml  one file per cable: what it joins (optional)
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
add the actual wires once they are known; the conductors stay the same.

## `config.yaml`

What each setting means is in `CONFIG.md`. Every one is written, even at its
default, so the file shows everything a project can change.

| field | | |
|---|---|---|
| `style` | required | the style of every kind of name: `net`, `box`, `connector`, `device`, `board`, `cable` |
| `sides` | required | the sides a net may start with; `[]` for none |
| `types` | required | every kind, each with its `types`; a kind not used is `{types: []}`; `ethernet` with more than two qualifiers also has `pairs` |
| `rules` | required | every adjustable rule, with its level |
| `palette` | required | `solid`, `striped` or `shaded`: the colors the project may use |
| `color` | required | `auto`, `fill` or `strict`: how wires get their colors |
| `colors` | with `fill` or `strict` | a color per type |
| `accept` | required | accepted entries by rule; `{}` for none |

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `config-fields` | every required field above is there, `colors` exactly when `color` is `fill` or `strict`, `style` lists every kind of name, `types` every kind (each with `types`), `rules` every adjustable rule | `lin: {types: []}` | no `lin` under `types`; no `accept` | error | |

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
| `bus-reach` | every conductor of a bus or link, followed along its wires, reaches every end in one piece. An end is reached as in `ends-match`. On SPI each chip select goes to one device, so there a conductor is only checked to be in one piece. Waits for a `cables/` folder, like `chain-order`; an `internal` bus is not checked | `CAN_BAT` `can:L` from the Accumulator to the Front Box | `CAN_S` `can:H` joining the Rear Box and the Front Box, and the HW boxes on a piece of their own; `can:L` never reaching `SW` | error | yes |
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
| `cable` | optional | the cable every pin with a `to` is on, when the connector takes one cable |
| `note` | optional | free text |
| `pins` | required | in the order they are printed |

Pin:

| field | | |
|---|---|---|
| `pin` | required | as printed on the connector, always a string (`'1'`, `a`) |
| `net` | with a net | the net (`CONFIG.md`); left out on `spare` and `unfitted` pins |
| `type` | required | the type (`CONFIG.md`) |
| `to` | optional | where the wire leaving this pin ends: the next box, or the device when it plugs straight in; a box or a device in `car.yaml`. A wire through several boxes is one `to` per hop, and following them gives the whole route |
| `cable` | optional | the cable the wire leaving this pin runs in (`cables/`), when it is not the connector's |
| `color` | optional | the color of that wire, when it is not its type's (`CONFIG.md`, Colors) |
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
| `pin-once` | no pin is written twice in one connector (case matters: `a` and `A` are two pins) | `'1'`, `'2'` | `'1'` twice in `APPS1` | error | |
| `pin-net` | a pin has a `net` unless its type is `spare` or `unfitted`, which never have one | `{pin: '4', type: spare}` | `{pin: '4', net: TE, type: spare}`, `{pin: '3', type: analog}` | error | |
| `to-known` | `to` is a box or a device | `to: Front Box`, `to: APPS1` | `to: Front box` | error | |
| `to-not-own-box` | `to` is not the pin's own box | `to: Front Box` in `Pedal Box` | `to: Pedal Box` in `Pedal Box` | error | |
| `spare-no-to` | a `spare` or `unfitted` pin has no `to`, `cable` or `color`: no wire leaves it | `{pin: '4', type: spare}` | `{pin: '4', type: spare, to: APPS1}` | error | |
| `to-reaches` | when `to` is a box, that box has a pin with the same net and type | `ACC` `power:24V` `to: PDU Box`, and `PDU Box` has an `ACC` `power:24V` pin | `to: Front Box` with no matching pin in `Front Box` | error | yes |
| `at-form` | `at` is `pass`, or `<board>:<pin>` with a board in `boards` | `te:RB0`, `pass` | `RB0`, `pdu:RB0` in a box without `pdu` | error | |
| `at-pass` | a `pass` pin has a pin with the same net and type on another connector of its box | | `pass` with nothing to pass to | error | yes |
| `pin-order` | the fields are in the order `pin`, `net`, `type`, `to`, `cable`, `color`, `at`, `note` | `{pin: '1', net: TE, type: ground}` | `{type: ground, pin: '1', net: TE}` | warn | yes |

## `cables/<cable>.yaml`

A cable file says what is true of the whole cable: its name and what it joins.
Which wires run in it is written on the pins, next to their `to` (`cable` on a
pin or a connector, `boxes/<box>.yaml`), so nothing is written twice.

```yaml
cable: Left Cooling
ends: [RearHub.cooling, Left Pump, Left Fan]
note: along the left side pod
```

The file is named after the cable, the same way a box is (`Left Cooling` is
`left_cooling.yaml`).

| field | | |
|---|---|---|
| `cable` | required | the cable's name, in the `cable` style (`CONFIG.md`) |
| `ends` | required | what it joins, at least two, in no order: connectors as `<box>.<connector>`, or devices. A cable with more than two ends branches |
| `part` | optional | the part number, for a bought cable |
| `note` | optional | free text |
| `wires` | optional | wires from one device straight to another, which no pin can carry |

A cable can join several connectors, and a connector can take several cables:
a 22 pin connector may take a 14 and an 8 wire cable. `RearHub.cooling` takes
two, each pin saying which:

```yaml
cable: Left Cooling
ends: [RearHub.cooling, Left Pump, Left Fan]
```

```yaml
cable: Right Cooling
ends: [RearHub.cooling, Right Pump, Right Fan]
```

```yaml
  cooling:
    part: DT06-12S
    pins:
      - {pin: '1', net: left_pump, type: power:12v, to: Left Pump, cable: Left Cooling, at: vcu:out6}
      - {pin: '3', net: right_pump, type: power:12v, to: Right Pump, cable: Right Cooling, at: vcu:out7}
```

The tool finds every wire from the pins. A pin on a cable goes `to` a device,
and the wire ends there; or `to` a box, and the wire ends on the one pin with
the same net and type, on the same cable, in that box.

A wire between two devices has no pin, so the cable lists it:

```yaml
cable: Shutdown Buttons
ends: [LVMS, ASMS]
wires:
  - {net: SDC, type: chain:D0, from: LVMS, to: ASMS}
```

| field | | |
|---|---|---|
| `net` | required | the net (`CONFIG.md`) |
| `type` | required | the type |
| `from` | required | a device end of the cable |
| `to` | required | another device end |
| `color` | optional | overrides the type's color (`CONFIG.md`, Colors) |

A conductor on three pins of one cable is spliced inside it; the drawings show
where. A project can leave `cables/` out until the wires are known, and
`to-cabled` does not run until there is a `cables/` folder.

Left to RapidHarness, after the concept phase: wire gauge, length, twisting
(a pair type already says it), current, and the pins on a device's own
connector.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `cable-file` | the file is named after its cable, and no two cables share a file name | `left_cooling.yaml` for `Left Cooling` | `left-cooling.yaml` | error | |
| `cable-fields` | `cable` and `ends` are there | | no `ends` | error | |
| `cable-ends` | there are at least two ends, each written once, each a connector of a box or a device | `[RearHub.cooling, Left Pump]` | `[RearHub.cooling]`, `[RearHub.Cooling, Left Pump]` | error | |
| `cable-known` | the `cable` of a connector or a pin is a cable | `cable: Left Cooling` | `cable: Left cooling` | error | |
| `cable-to` | a pin with its own `cable` has a `to`: a wire needs a far end | `{pin: '1', ..., to: Left Pump, cable: Left Cooling}` | `{pin: '1', ..., cable: Left Cooling}` | error | |
| `cable-on-end` | a pin's connector is an end of its cable, and so is its `to`: the device, or a connector of that box | `RearHub.cooling` pin `to: Left Pump` on `Left Cooling` | the same pin on `Right Cooling` | error | |
| `cable-far-pin` | a pin going to a box has exactly one pin there with its net and type on the same cable | `RearHub.front.A` and `Bulkhead.rear.A`, both on `Rear` | no such pin on `Rear`, or two | error | |
| `wire-fields` | a listed wire has `net`, `type`, `from` and `to`, two different device ends of its cable | `{net: SDC, type: chain:D0, from: LVMS, to: ASMS}` | `{net: SDC, type: chain:D0, from: LVMS}` | error | |
| `wire-color` | the two pins of a wire do not give it two colors | `color: blue` on one pin, or the same on both | `blue` on one, `white` on the other | error | |
| `cable-used` | every cable has a wire | | a cable no pin is on | warn | yes |
| `to-cabled` | every pin with a `to` is on a cable, once there is a `cables/` folder | `RearHub.cooling.1` on `Left Cooling` | `Nose.imu.1` on no cable | warn | yes |
| `pair-cable` | the two wires of a twisted pair going to the same place are on the same cable, so they can be twisted. The pairs are `can`, `rs485`, `ethernet` (each pair of a link, CONFIG.md, Ethernet) and `pair` but `hv` (HV+ and HV- run as two single cables). Reported on the pin with the pair's first qualifier | `RearHub.front.G` `can:h` and `.H` `can:l`, both on `Rear Signal` | the same two pins, one on `Rear Signal` and one on `Rear Power` | warn | yes |

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
- `config.yaml` writes every setting, defaults included: nothing the project can
  change is hidden in the tool.
- A cable file has only what is true of the whole cable. Each pin names its
  cable (or its connector does), so no wire is written twice. `ends` has no
  order. Only a wire between two devices is listed in the cable. No `splices`:
  a conductor on three pins of one cable is a splice.
