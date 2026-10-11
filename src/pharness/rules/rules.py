"""Every rule the tool checks, as in the tables of CONFIG.md and STRUCT.md.

Each rule has its default level and whether a project may change it under
`rules` or accept one entry of it under `accept` in config.yaml.
"""

from typing import NamedTuple


class Rule(NamedTuple):
    level: str        # "error" or "warn"
    adjustable: bool  # may a project change it


ERROR = Rule("error", False)
WARN = Rule("warn", False)

RULES = {
    # STRUCT.md, Files
    "yaml": ERROR,
    "key-once": ERROR,
    "field-known": ERROR,
    "field-shape": ERROR,

    # STRUCT.md, config.yaml
    "config-fields": ERROR,

    # CONFIG.md, the start
    "conductor-one-end": Rule("warn", True),

    # CONFIG.md, Styles
    "style-kind": ERROR,
    "style-name": ERROR,
    "style-net": ERROR,
    "net-words-case": ERROR,

    # CONFIG.md, Nets
    "net-style": ERROR,
    "net-letter": ERROR,
    "net-side-first": ERROR,
    "net-thing": ERROR,
    "net-no-label": ERROR,

    # CONFIG.md, Types
    "type-kinds": ERROR,
    "kind-form": ERROR,
    "type-word-case": ERROR,
    "type-word-twice": ERROR,
    "type-reserved": ERROR,
    "pin-type": ERROR,
    "unfitted-note": Rule("error", True),

    # CONFIG.md, Labels
    "label-unique": ERROR,

    # CONFIG.md, Buses
    "bus-name": ERROR,
    "bus-net": ERROR,
    "bus-type": ERROR,

    # CONFIG.md, Ethernet
    "eth-link-name": ERROR,
    "eth-net": ERROR,
    "eth-type": ERROR,

    # CONFIG.md, Chains
    "chain-node": ERROR,
    "chain-out-unique": ERROR,
    "chain-type": ERROR,
    "chain-out-used": Rule("warn", True),

    # CONFIG.md, Boxes, connectors, devices, boards, cables
    "box-style": ERROR,
    "connector-style": ERROR,
    "device-style": ERROR,
    "board-style": ERROR,
    "box-not-board": ERROR,
    "box-not-device": ERROR,
    "cable-style": ERROR,

    # CONFIG.md, Rule levels
    "rule-known": ERROR,
    "rule-level": ERROR,
    "rule-fixed": ERROR,
    "accept-reason": ERROR,
    "accept-known": ERROR,
    "accept-used": WARN,

    # STRUCT.md, car.yaml
    "car-name": ERROR,
    "bus-fields": ERROR,
    "chain-fields": ERROR,
    "ends-known": ERROR,
    "ends-match": Rule("error", True),
    "bus-internal": Rule("error", True),
    "device-used": Rule("warn", True),

    # STRUCT.md, boxes/<box>.yaml
    "box-file": ERROR,
    "box-fields": ERROR,
    "connector-pins": ERROR,
    "pin-fields": ERROR,
    "pin-string": ERROR,
    "pin-once": ERROR,
    "pin-net": ERROR,
    "to-known": ERROR,
    "to-not-own-box": ERROR,
    "spare-no-to": ERROR,
    "to-reaches": Rule("error", True),
    "at-form": ERROR,
    "at-pass": Rule("error", True),
    "pin-order": Rule("warn", True),

    # STRUCT.md, cables/<cable>.yaml
    "cable-file": ERROR,
    "cable-fields": ERROR,
    "cable-ends": ERROR,
    "cable-known": ERROR,
    "cable-to": ERROR,
    "cable-on-end": ERROR,
    "cable-far-pin": ERROR,
    "wire-fields": ERROR,
    "cable-used": Rule("warn", True),
    "to-cabled": Rule("warn", True),
}

LEVELS = ["error", "warn", "off"]
