"""What config.yaml sets, once checked: the styles, the sides, the kinds of
type and the colors (CONFIG.md: Styles, Types, Colors). Checking and reading
it is checks/config.py."""

from dataclasses import dataclass, field

# The kinds are fixed, since the tool needs them; the words in them are the project's.
KINDS = ["supply", "ground", "signal", "pair", "phase", "can", "lin", "rs485", "i2c",
         "spi", "serial", "shield", "ethernet", "chain", "no_net"]
BUS_KINDS = ["can", "lin", "rs485", "i2c", "spi"]
KINDS_WITHOUT_WORDS = ["chain", "no_net"]   # neither a label nor qualifiers
PAIR_KINDS = ["pair", "can", "rs485", "ethernet"]   # twisted in pairs, but hv

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
    pairs: list = field(default_factory=list)   # [(qualifier, qualifier)], as eth-pairs passed

    def twisted(self):
        """The pairs of its qualifiers that are twisted together: the two
        qualifiers when there are two, else its `pairs`."""
        if self.name not in PAIR_KINDS:
            return []
        if len(self.qualifiers) == 2:
            return [tuple(self.qualifiers)]
        return self.pairs


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

    def twisted_pairs(self):
        """Every pair of types twisted together, as (first, second): the
        pair kinds' words with each pair of qualifiers, but `hv` (STRUCT.md,
        pair-cable)."""
        pairs = []
        for kind in self.kinds.values():
            for word in kind.words:
                if word == "hv":
                    continue
                pairs.extend((f"{word}:{a}", f"{word}:{b}") for a, b in kind.twisted())
        return pairs
