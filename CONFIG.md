# Config

Every name in a project follows these rules. The tool checks them exactly: a name
either follows them or it is reported. Nothing is matched loosely, so `CAN_E` and
`can_e` are two different names and the second one is wrong.

A pin says two things about its conductor: the **net** it belongs to (whose it
is) and its **type** (what the conductor is). Each is written once:

```yaml
- {pin: '1', net: APPS1, type: ground}
- {pin: '2', net: APPS1, type: power:5V}
- {pin: '3', net: APPS1, type: analog}
```

Two pins are the same conductor when they have the same net and the same type.
A pin whose net or type is misspelled is a conductor of its own, with nothing at
the other end, and is reported as such.

The rules come in two parts. The grammar below is the same for every project and
cannot be changed. How names are written, the sides a net may use and the types
a pin may have are the project's own, listed in its `config.yaml`:

```yaml
style:
  net: upper_snake
  box: title
  connector: title
  device: title
  board: kebab

sides: [LEFT, RIGHT, FRONT, REAR, FL, FR, RL, RR]

types:
  supply:   {types: [power], qualifiers: [24V, 12V, 5V, 3V3]}
  ground:   {types: [ground], label: GND}
  signal:   {types: [analog, digital, pwm, freq], label: SIG}
  pair:     {types: [analog, digital, hv], qualifiers: [P, N]}
  can:      {types: [can], qualifiers: [H, L]}
  serial:   {types: [serial], qualifiers: [TX, RX]}
  shield:   {types: [shield], label: SHIELD}
  ethernet: {types: [ethernet], qualifiers: [1, 2, 3, 4, 5, 6, 7, 8]}
  chain:    {types: [chain]}
  no_net:   {types: [spare, unfitted]}
```

The examples here use these words and the default styles.

## Styles

Every kind of name is written in one style, set under `style`. Left out, a kind
keeps its default, and so does a project with no `style` at all:

| kind | default | example |
|---|---|---|
| `net` | `upper_snake` | `FL_SUSPOT`, `CAN_E` |
| `box` | `title` | `Front Box`, `HW FL Box` |
| `connector` | `title` | `Rear Supply` |
| `device` | `title` | `Sus Pot FL`, `Cylinder Detection 0` |
| `board` | `kebab` | `te`, `suspot-front`, `steering-wheel` |

The styles:

| style | example | words |
|---|---|---|
| `upper_snake` | `REAR_BOX` | upper case letters and digits, joined by single `_` |
| `snake` | `rear_box` | lower case letters and digits, joined by single `_` |
| `upper_kebab` | `REAR-BOX` | upper case letters and digits, joined by single `-` |
| `kebab` | `rear-box` | lower case letters and digits, joined by single `-` |
| `title` | `Rear Box` | joined by single spaces, each a capital and then lower case letters and digits, all capitals, or all capitals and a plural `s` (`NTCs`) |
| `pascal` | `RearBox` | one word starting with a capital |
| `camel` | `rearBox` | one word starting with a lower case letter |

A word of only digits fits every style (`Cylinder Detection 0`, `SOL_1`).

A net needs a separator to tell its side and index from the rest, so it is
`upper_snake`, `snake`, `upper_kebab` or `kebab`. Buses, links and chains are
nets and follow `net`. The words a net is built from follow its case too: the
`sides`, and the labels and qualifiers in `types`, which end up in wire labels
(`snake` nets need `left`, `gnd`, `h`, `3v3`).

Not styled: pins, written exactly as printed; types, already a closed list; the
car's name.

## Nets

A net name starts with a letter and is in the `net` style. It is built from
words, most general first:

```
[SIDE_]THING[_INDEX]
```

| part | | examples |
|---|---|---|
| SIDE | where on the car, when there is more than one: one of `sides` | `LEFT_PUMP` |
| THING | what the net belongs to: one or more words, never starting with a side or ending in a word of only digits | `PUMP`, `ACU`, `SUSPOT`, `RTD_BUTTON` |
| INDEX | which one, when there are several: a word of only digits, numbered the way the team numbers them | `SOL_0`, `SOL_1` |

THING words are the project's own and are not listed anywhere: the tool checks
that each part is in its place, not which words it uses. A net spelled two ways
is caught by the wiring, since each spelling ends up with nothing at the other
end. A net may use `SUPPLY`, `POWER` and the like when they tell two things
apart: `STA_SUPPLY` is the STA's supply, `STA` its serial port.

Not allowed:

- anything its style does not allow: parentheses, `>`, spaces, double
  separators (`24V(1)`, `LVMS_>BSPD`)
- a side after anything else: the side always comes first (`BUZZER_L` is
  `LEFT_BUZZER`)
- what the type already says: a net never ends in a label or a qualifier other
  than an index (`APPS1_5V`, `APPS1_SIG`, `PDU_GND`, `CAN_E_H` are `APPS1`, `PDU`,
  `CAN_E`); `SOL_1` is fine, `1` is its index

## Types

Every pin has a type, and the type says which conductor of the net the pin is
on. Types are lower case, written `word` or `word:qualifier`.

The kinds under `types` are fixed, since the tool needs them; the words in them
are the project's (a team with SENT sensors adds `sent` under `signal`). A kind
has either a `label` or `qualifiers`:

- with a `label`, the type is one of its words: `ground`, `analog`, `shield`
- with `qualifiers`, the type is a word and a qualifier: `power:24V`, `can:H`,
  `digital:P`, `ethernet:3`. Two-qualifier kinds keep their order: positive and
  negative, high and low, transmit and receive

A word may be in two kinds when one has qualifiers and the other does not:
`analog` is a signal, `analog:P` half of a pair.

| kind | conductor | example pin |
|---|---|---|
| `supply` | supply at that voltage | `LEFT_PUMP`, `power:24V` |
| `ground` | return | `LEFT_PUMP`, `ground` |
| `signal` | a single analog or digital signal, every one of them | `FL_SUSPOT`, `analog` |
| `pair` | the two halves of a differential pair, or the high voltage | `FR_ENCODER_DATA`, `digital:P`; `HV`, `hv:N` |
| `can` | CAN high and low, only on a bus (below) | `CAN_E`, `can:H` |
| `serial` | serial, as seen from the board that owns the port; the far end keeps the same type | `STA`, `serial:TX` |
| `shield` | cable screen, on the net of the thing it screens, or of the cable when it carries several things. A screen that belongs to neither has no net | `APPS1`, `shield` |
| `ethernet` | one conductor of an Ethernet link, only on a link (below) | `ETH_RPI`, `ethernet:3` |
| `chain` | a point on a chain (below) | `SDC`, `chain:D5` |
| `no_net` | `spare` or `unfitted`, with no net | |

A load (a lamp, a buzzer, a coil) is not a pair: it is a supply and its return,
`ASSI_BLUE` as `power:24V` and `ground`.

Three type words mean something to the tool and keep that meaning: `hv` (high
voltage, kept apart from the rest), `spare` and `unfitted`. `spare` is a
position nothing uses. `unfitted` is a position that is wired but has nothing on
the far end, such as a part that was dropped; a `note` on the pin says what it
was for.

## Labels

Drawings, wire lists and programs need one name per wire. The tool builds it as
`<net>_<label>`, the label being the kind's `label` or the type's qualifier, joined
by the net style's separator:

| net | type | wire |
|---|---|---|
| `APPS1` | `power:5V` | `APPS1_5V` |
| `APPS1` | `ground` | `APPS1_GND` |
| `APPS1` | `analog` | `APPS1_SIG` |
| `CAN_E` | `can:H` | `CAN_E_H` |
| `ETH_RPI` | `ethernet:3` | `ETH_RPI_3` |
| `SDC` | `chain:D5` | `SDC_D5` |

The labels are never written in the harness files.

## CAN

A CAN net is exactly `CAN_<BUS>`, a bus listed in `car.yaml`, and its pins are
`can:H` or `can:L`. Nothing else may start with `CAN_`, so the supply of a CAN
board is `CAN2SPI`, not `CAN_2SPI`. A CAN pin on a connector that is not on any
bus is `spare`.

## Ethernet

An Ethernet net is exactly `ETH_<LINK>`, and the qualifier of each pin is the
conductor: with the RJ45 pin numbers as qualifiers, the pin of the RJ45 it maps
to (`ETH_RPI` with `ethernet:3`, not `ETHERNET_RPI_(3)`). A single pair link
would use `[P, N]`. `<LINK>` names the link, not the box it starts from. Nothing
else starts with `ETH_`: the supply of a switch is named after the switch.

## Chains

A chain is a series loop where the order matters: the shutdown circuit, a high
voltage interlock loop, a line of emergency buttons. It is declared in `car.yaml`
with its nodes in the order current flows, and a label for the conductor that
leaves each node:

```yaml
chains:
  SDC:
    - {node: LVMS, out: D0}
    - {node: ASMS, out: D1}
    - {node: RES,  out: D2}
  HVIL:
    - {node: Accumulator HV, out: 1}
    - {node: Inverter HV,    out: 2}
```

The whole chain is one net, named after it, and the conductor leaving a node is
the type `chain:<out>`: net `SDC` with `chain:D0`, `chain:D1`, `chain:D2`. Those
are the only types a pin on a chain may have. The labels are the project's own
(FST uses the tap numbers from its SDC diagram).

What feeds the first node is not part of the chain: it is a supply (`LVS`,
`power:24V`). A box that senses a point on a chain carries that point's net and
type. A sense line named by its slot on a board (`DATA_28`) is not a name.

## Boxes, connectors, devices, boards

- **Box**: in the `box` style. A box is never named like a board inside it,
  whatever their styles: the box holding the `pdu` board is `PDU Box`.
- **Board**: in the `board` style, named after its firmware: `te`, `suspot-front`.
- **Connector**: in the `connector` style, unique in its box, named by what it
  connects to or does, not by its part number: `Rear Supply`, `CAN Analog`. The
  part number goes in `part:` (`ASL006-05SA (yellow)` is a part, not a name).
- **Device**: in the `device` style: `Sus Pot FL`, `Brake Light`.
- **Pin**: exactly as printed on the connector, case matters (`a` and `A` are two
  pins on a Deutsch AS).
