"""What config.yaml sets, once checked: the styles, the sides, the kinds of
type and the colors (CONFIG.md: Styles, Types, Colors). Checking and reading
it is checks/config.py."""

from dataclasses import dataclass, field

# The kinds are fixed, since the tool needs them; the words in them are the project's.
KINDS = ["supply", "ground", "signal", "pair", "phase", "can", "lin", "rs485", "i2c",
         "spi", "serial", "shield", "ethernet", "chain", "no_net"]
BUS_KINDS = ["can", "lin", "rs485", "i2c", "spi"]
KINDS_WITHOUT_WORDS = ["chain", "no_net"]   # neither a label nor qualifiers

# Type words that mean something to the tool, and the kinds they may be in.
RESERVED = {
    "hv": ["pair", "phase"],
    "spare": ["no_net"],
    "unfitted": ["no_net"],
}


@dataclass
class Kind:
    """One kind under `types`: its words, and its label or its qualifiers."""

    name: str
    words: list
    label: str | None
    qualifiers: list   # as strings: 1 and '1' are the same qualifier
    line: int
    well_formed: bool  # kind-form passed; if not, pins are not judged by its form


@dataclass
class Settings:
    """What config.yaml says, once checked."""

    style: dict   # kind of name -> style, None when it was set wrong
    sides: list
    kinds: dict   # kind name -> Kind
    palette: str | None = "striped"   # None when set wrong: colors are not judged
    color: str | None = "auto"        # auto, fill or strict; None when set wrong
    colors: dict = field(default_factory=dict)      # type -> color, as written
    colors_at: dict = field(default_factory=dict)   # type -> file:line
    colors_where: str = "config.yaml"               # where `colors` is, or `color`
