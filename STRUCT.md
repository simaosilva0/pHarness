# Structure

The files of a project and every field in them. Names and types inside them
follow `CONFIG.md`.

## Files

```
<project>/
  config.yaml          styles, sides and types (CONFIG.md)
  car.yaml             the car: devices, buses, links, chains
  boxes/<box>.yaml     one file per box: its connectors and their pins
  cables/<cable>.yaml  one file per cable: its wires (optional)
```

Every file is plain YAML. A key written twice is an error, every name is
matched exactly, and every problem is reported with its file and line. A field
not listed here is an error, so a typo in a field name never goes unnoticed.

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
| `devices` | optional | every part that is not a box but has pins wired to it: sensors, switches, lamps, motors. Keyed by name (device rule in `CONFIG.md`), each with an optional `note` |
| `buses` | optional | CAN buses, keyed by name (`CAN_<BUS>`). `bitrate`, its `ends` (the boxes and devices on it), `internal: true` when it never leaves its box |
| `links` | optional | Ethernet links, keyed by name (`ETH_<LINK>`), with their `ends` (boxes or devices) |
| `chains` | optional | series loops in the order current flows (`CONFIG.md`). Each node has a `node` name, an `out` label and, when the node is inside a box, that `box`; a node outside every box is a device |

The boxes of the car are the files in `boxes/`; they are not listed again.

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
nothing lined up, so a hand edit never forces realigning its neighbours:

```yaml
      - {pin: '1', net: PEDAL_BOX, type: shield}
      - {pin: '2', net: TE, type: power:24V, to: Front Box}
      - {pin: '11', type: spare}
```

Inside a box, pins with the same net and type are joined: a supply that comes in
on one connector and leaves on another is one conductor without a wire.

## `cables/<cable>.yaml`

Shape only; the details are decided with step 9.

```yaml
cable: Pedal Box Splitter
ends: [Pedal Box.Splitter, Splitter Box.In]
wires: by-net
```

| field | | |
|---|---|---|
| `cable` | required | the cable's name, same rule as a box |
| `ends` | required | the connectors it joins, as `<box>.<connector>` |
| `wires` | required | `by-net`: one wire between every pair of pins on the two ends with the same net and type. Or a list of wires, each `{from: <box>.<connector>.<pin>, to: ...}`, for anything else |
| `splices` | optional | where one conductor splits inside the cable |

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
- Buses and links list their `ends`, boxes or devices.
- `part` is optional.
