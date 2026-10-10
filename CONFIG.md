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
  phase:    {types: [hv], qualifiers: [U, V, W]}
  can:      {types: [can], qualifiers: [H, L]}
  serial:   {types: [serial], qualifiers: [TX, RX]}
  shield:   {types: [shield], label: SHIELD}
  ethernet: {types: [ethernet], qualifiers: [1, 2, 3, 4, 5, 6, 7, 8]}
  chain:    {types: [chain]}
  no_net:   {types: [spare, unfitted]}
```

The examples here use these words and the default styles.

Each section ends with the rules the tool checks, one per row: when an entry
passes, an example that passes and one that does not, its level, and whether a
project may change that level. At `error` the project is wrong: the tool reports
everything it finds, then produces nothing. At `warn` it is accepted but
printed, so someone looks at it. An `adjustable` rule can be set to another
level in `config.yaml` (Rule levels, at the end). The examples use the default styles; under
another style the same rules hold with its separator and case. Rules about
meaning, such as a connector named by what it connects to, have no row: only a
person can check them.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `conductor-one-end` | a conductor that is not a `shield` has at least two pins, or one pin whose `to` is a device. A screen is usually tied down at one end only | `APPS1` `analog` with `to: APPS1`; `PEDAL_BOX` `shield` on one pin | `CAN_BAT` `can:L` on one pin, no `to` | warn | yes |

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
`sides`, the labels and qualifiers in `types` and the `out`s of chains, which
end up in wire labels (`snake` nets need `left`, `gnd`, `h`, `3v3`, `d5`).

Not styled: pins, written exactly as printed; types, already a closed list; the
car's name.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `style-kind` | every key under `style` is `net`, `box`, `connector`, `device` or `board` | `box: title` | `wire: snake` | error | |
| `style-name` | every style is one of the seven above | `net: kebab` | `net: lower` | error | |
| `style-net` | the `net` style is `upper_snake`, `snake`, `upper_kebab` or `kebab` | `net: snake` | `net: pascal` | error | |
| `net-words-case` | every side, label, qualifier and chain `out` is one word in the net's case: letters and digits, no separator; digits always pass | `LEFT`, `5V`, `8`, `D5` | `Left`, `5v`, `d5`, `D_5` | error | |

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

The rules apply to every net: on pins, and the names of buses, links and chains.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `net-style` | the net is in the `net` style | `FL_SUSPOT` | `fl_suspot`, `24V(1)`, `LVMS_>BSPD` | error | |
| `net-letter` | it starts with a letter | `APPS1` | `24V` | error | |
| `net-side-first` | a side is only ever the first word | `LEFT_BUZZER` | `BUZZER_LEFT`, `FL_LEFT_PUMP` | error | |
| `net-thing` | at least one word is neither the leading side nor the trailing index | `LEFT_PUMP`, `SOL_1` | `LEFT`, `FL_1` | error | |
| `net-no-label` | the last word is not a label, a qualifier or a chain `out`, unless it is only digits (then it is an index) | `SOL_1`, `DCDC_1` | `APPS1_SIG`, `APPS1_5V`, `CAN_E_H`, `SDC_D5` | error | |

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
| `supply` | supply at that voltage. A qualifier is one word, so 3.3 V is `3V3` and −12 V would be `N12V` | `LEFT_PUMP`, `power:24V` |
| `ground` | return | `LEFT_PUMP`, `ground` |
| `signal` | a single analog or digital signal, every one of them. A net has one signal: a fan's speed command and tachometer are two nets, `LEFT_FAN` `pwm` and `LEFT_FAN_TACH` `freq`, since both would be `LEFT_FAN_SIG` | `FL_SUSPOT`, `analog` |
| `pair` | the two halves of a differential pair, or the high voltage | `FR_ENCODER_DATA`, `digital:P`; `HV`, `hv:N` |
| `phase` | the phases of a motor or another polyphase load | `FL_MOTOR`, `hv:U` |
| `can` | CAN high and low, only on a CAN bus (Buses) | `CAN_E`, `can:H` |
| `lin` | the one LIN wire, only on a LIN bus | `LIN_WHEEL`, `lin` |
| `rs485` | RS-485 A and B, only on an RS-485 bus | `RS485_RIDE`, `rs485:A` |
| `i2c` | I2C data and clock, only on an I2C bus | `I2C_CABIN`, `i2c:SDA` |
| `spi` | SPI clock, data and each device's chip select, only on an SPI bus | `SPI_STRAIN`, `spi:CS0` |
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

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `type-kinds` | every kind under `types` is one of the fifteen above | `serial` | `usb` | error | |
| `kind-form` | a kind has a `label` or `qualifiers`, not both; `chain` and `no_net` have neither | `ground: {types: [ground], label: GND}` | `ground: {types: [ground], label: GND, qualifiers: [A]}` | error | |
| `type-word-case` | every type word is lower case letters and digits | `sent` | `SENT`, `can-fd` | error | |
| `type-word-twice` | a word is in two kinds only when exactly one of them has qualifiers, or it is `hv` in `pair` and `phase` | `analog` in `signal` and `pair` | `power` in `supply` and `pair` | error | |
| `type-reserved` | `hv` is in `pair`, and may also be in `phase`; `spare` and `unfitted` are in `no_net` | | `spare` under `signal` | error | |
| `pin-type` | a pin's type is a word of a kind with a `label` or of `no_net`, alone; or a word of a kind with `qualifiers` and one of them, as `word:qualifier`. Chain types are under Chains | `analog`, `analog:P`, `power:24V` | `power`, `power:48V`, `ground:A`, `Analog` | error | |
| `unfitted-note` | an `unfitted` pin has a `note` | `{pin: '7', type: unfitted, note: TITS}` | `{pin: '7', type: unfitted}` | error | yes |

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

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `label-unique` | no two conductors get the same wire label | `APPS1` `analog` and `APPS1` `ground` | `LEFT_FAN` `pwm` and `LEFT_FAN` `freq`, both `LEFT_FAN_SIG` | error | |

## Buses

A bus is a net that several boxes and devices share. Five kinds are buses: `can`,
`lin`, `rs485`, `i2c` and `spi`. A bus net is exactly `<KIND>_<BUS>`, the kind's
name first, in the net's case: `CAN_E`, `LIN_WHEEL`, `RS485_RIDE`, `I2C_CABIN`,
`SPI_STRAIN`. It is listed in `car.yaml`, and its pins have types of its kind
only. Nothing else may start with a bus kind's name, so the supply of a CAN
board is `CAN2SPI`, not `CAN_2SPI`. A bus pin on a connector that is not on any
bus is `spare`.

The qualifiers are the project's, in its `types`:

```yaml
types:
  can:   {types: [can], qualifiers: [H, L]}
  lin:   {types: [lin], label: DATA}
  rs485: {types: [rs485], qualifiers: [A, B]}
  i2c:   {types: [i2c], qualifiers: [SDA, SCL]}
  spi:   {types: [spi], qualifiers: [SCK, MOSI, MISO, CS0, CS1]}
```

LIN has one wire, so its kind has a label (`LIN_WHEEL_DATA`). On SPI the clock
and data are shared, and every device has its own chip select: `SPI_STRAIN`
`spi:CS0` goes to one device, `spi:CS1` to the next. A bus device's supply and
ground are on its own net, as on any device.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `bus-name` | every bus in `car.yaml` is a bus kind's name and at least one more word | `CAN_E`, `I2C_CABIN` | `CAN`, `E`, `UART_GPS` | error | |
| `bus-net` | a net whose first word is a bus kind's name is a bus | `CAN_E` | `CAN_2SPI` | error | |
| `bus-type` | a pin on a bus has a type of the bus's kind, and those types are only on buses of that kind | `CAN_E` `can:H` | `CAN_E` `analog`, `CAN_E` `lin`, `CAN2SPI` `can:H` | error | |

## Ethernet

An Ethernet net is exactly `ETH_<LINK>`, and the qualifier of each pin is the
conductor: with the RJ45 pin numbers as qualifiers, the pin of the RJ45 it maps
to (`ETH_RPI` with `ethernet:3`, not `ETHERNET_RPI_(3)`). A single pair link
would use `[P, N]`. Like a bus, a link is listed in `car.yaml`. `<LINK>` names the link, not the box it starts from. Nothing
else starts with `ETH_`: the supply of a switch is named after the switch.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `eth-link-name` | every link in `car.yaml` is `ETH` and at least one more word | `ETH_RPI` | `ETH`, `RPI` | error | |
| `eth-net` | a net whose first word is `ETH` is a link | `ETH_RPI` | `ETH_SWITCH` | error | |
| `eth-type` | a pin on a link is `ethernet:<qualifier>`, and `ethernet` types are only on links | `ETH_RPI` `ethernet:3` | `ETH_RPI` `analog`, `ETHERNET_SWITCH` `ethernet:3` | error | |

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

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `chain-node` | a node with a `box` names a box; a node without one is a device | `{node: LVMS, out: D0}`, `{node: RES, out: D2, box: RES}` | `{node: ACU, out: D3, box: ACU}` with no box `ACU` | error | |
| `chain-out-unique` | every `out` appears once in its chain | `D0`, `D1`, `D2` | two nodes with `out: D5` | error | |
| `chain-type` | a pin on a chain is `chain:<out>` with an `out` of that chain, and `chain` types are only on chains | `SDC` `chain:D5` | `SDC` `power:24V`, `SDC` `chain:D99`, `LVS` `chain:D0` | error | |
| `chain-out-used` | every `out` is on at least one pin, unless its node and the next node are in the same box | `D5` on Accumulator Data 12; `D6` on no pin, IMD and AMS both in the Accumulator | `D3` on no pin | warn | yes |

Whether the loop really runs from each node to the next is checked once cables
exist (step 9): a stretch from one device straight to another, such as LVMS to
ASMS, is in no box file, only the boxes' taps on it are.

## Boxes, connectors, devices, boards

- **Box**: in the `box` style. A box is never named like a board inside it,
  whatever their styles: the box holding the `pdu` board is `PDU Box`.
- **Board**: in the `board` style, named after its firmware: `te`, `suspot-front`.
  Anything inside a box that pins land on counts as a board; one with no
  firmware (a fuse block, a relay board, a BSPD) is named after what it is:
  `fuses`, `bspd`.
- **Connector**: in the `connector` style, unique in its box, named by what it
  connects to or does, not by its part number: `Rear Supply`, `CAN Analog`. The
  part number goes in `part:` (`ASL006-05SA (yellow)` is a part, not a name).
- **Device**: in the `device` style: `Sus Pot FL`, `Brake Light`.
- **Pin**: exactly as printed on the connector, case matters (`a` and `A` are two
  pins on a Deutsch AS).

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `box-style` | the box is in the `box` style | `Front Box`, `HW FL Box` | `Front box`, `front_box` | error | |
| `connector-style` | the connector is in the `connector` style | `Rear Supply`, `CAN Analog` | `rear supply`, `ASL006-05SA (yellow)` | error | |
| `device-style` | the device is in the `device` style, and so is the name of a chain node inside a box, named after the part it is | `Sus Pot FL`, `Cylinder Detection 0` | `sus pot FL`, `Sus_Pot_FL` | error | |
| `board-style` | the board is in the `board` style | `te`, `suspot-front` | `TE`, `suspot_front` | error | |
| `box-not-board` | the box is not named like a board in it, ignoring case and separators | `PDU Box` holding `pdu` | `PDU` holding `pdu` | error | |

## Rule levels

A project changes the level of an adjustable rule under `rules` in
`config.yaml`. A rule left out keeps the level in its table:

```yaml
rules:
  conductor-one-end: error
  pin-order: off
```

Fixed rules are never listed, since their level cannot change.

| level | |
|---|---|
| `error` | the project is wrong: everything is reported, then the tool produces nothing |
| `warn` | printed, and the tool goes on |
| `off` | the check does not run |

The adjustable rules are about completeness: a harness in its concept phase may
not have them yet, such as a wire nobody has followed to its far end or a device
no pin reaches. The rest are fixed: the tool needs them to read the project at
all (the files, their fields, every reference), or they are the grammar, which
is the same for every project.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `rule-known` | every key under `rules` is a rule in these tables | `pin-order: off` | `pin-orders: off` | error | |
| `rule-level` | every level is `error`, `warn` or `off` | `warn` | `pass`, `listed` | error | |
| `rule-fixed` | only adjustable rules are listed | `ends-match: warn` | `net-style: warn` | error | |

### Accepting one entry

An entry that breaks an adjustable rule, and is known and fine, is accepted
under `accept` with the reason, so the rule stays on for everything else:

```yaml
accept:
  to-reaches:
    Accumulator.Data.11: the Front Box D7 pin is not known yet
  chain-out-used:
    SDC chain:D3: ACU to RESB not wired yet
  bus-internal:
    CAN_X1: spare bus, kept for later
```

The report prints every problem of an adjustable rule with its entry, as it is
written here, so accepting it is a copy. An accepted entry is not reported. The list stays in one place, away from the
harness files, and the tool keeps it honest: an entry that no longer exists (a
pin was renamed) is an error, and one that no longer breaks its rule is
printed, so it can be removed. While its rule is `off`, or another mistake keeps
the rule from judging it (a misspelled end, a box file with no `box`), an entry
is not called stale.

| rule | entry | example |
|---|---|---|
| `to-reaches`, `at-pass`, `unfitted-note`, `pin-order` | a pin, `<box>.<connector>.<pin>` | `Accumulator.Data.11` |
| `conductor-one-end` | a conductor, `<net> <type>` | `CAN_BAT can:L` |
| `chain-out-used` | a chain out, `<chain> chain:<out>` | `SDC chain:D3` |
| `ends-match`, `bus-internal` | a bus or link | `CAN_X1` |
| `device-used` | a device | `RPI Fan` |

`rule-known` and `rule-fixed` hold for the rules under `accept` too.

| rule | passes when | ok | wrong | level | adjustable |
|---|---|---|---|---|---|
| `accept-reason` | every accepted entry has a reason | `CAN_X1: spare bus, kept for later` | `CAN_X1: ''` | error | |
| `accept-known` | every accepted entry exists | `Accumulator.Data.11` | `Accumulator.Data.99`, `Accumulator / Data / 11` | error | |
| `accept-used` | every accepted entry still breaks its rule | | `Pedal Box.In.1` under `to-reaches`, which it reaches | warn | |
