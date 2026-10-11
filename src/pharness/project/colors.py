"""Wire colors (CONFIG.md, Colors): the palettes, and the color of every type.

The tool fills in the color of every type the project left out. Each kind is
a family: a base color, then the base with a stripe. Every type takes the
first color of its family nobody has taken yet.
"""

from .labels import split_type

# IEC 60757.
TWELVE = ["black", "brown", "red", "orange", "yellow", "green", "blue", "violet",
          "grey", "white", "pink", "turquoise"]
SHADES = ["light blue", "dark blue", "light green", "dark green", "light grey", "beige"]

PALETTES = ["solid", "striped", "shaded"]
MODES = ["auto", "fill", "strict"]

# The order the stripes of a family are tried in.
STRIPES = ["white", "black", "green", "blue", "red", "yellow", "violet", "grey", "brown",
           "pink", "turquoise"]

# The kinds in the order they pick, each with its base color. Shields, spare
# and unfitted pins have no colored wire; chains and hv have one color each.
FAMILIES = [
    ("supply", "red"),
    ("ground", "black"),
    ("signal", "white"),
    ("pair", "blue"),
    ("phase", "black"),
    ("can", "yellow"),
    ("lin", "violet"),
    ("rs485", "turquoise"),
    ("i2c", "pink"),
    ("spi", "violet"),
    ("serial", "grey"),
    ("ethernet", "green"),
]
CAN_SECOND = "green"   # CAN low, by convention
CHAIN = "brown"        # a chain reads as one line
TAP = "brown/white"    # a wire that only taps a chain, as a branch of that line
HV = "orange"          # high voltage, at a glance


def in_palette(color, palette):
    """Whether a color is written in the palette: one color, or `<base>/<stripe>`
    of two different ones when the palette has stripes."""
    if not isinstance(color, str):
        return False
    allowed = list(TWELVE)
    if palette == "shaded":
        allowed += SHADES
    parts = color.split("/")
    if len(parts) == 1:
        return color in allowed
    if len(parts) != 2 or palette == "solid":
        return False
    base, stripe = parts
    return base in allowed and stripe in allowed and base != stripe


def base_of(color):
    """`green/yellow` -> green."""
    return str(color).split("/")[0]


def is_hv(type_):
    word, _ = split_type(type_)
    return word == "hv"


def kind_types(kind):
    """The types of a kind, in the order `types` writes them: each word with
    each of its qualifiers, or each word alone."""
    if kind.qualifiers:
        return [f"{word}:{qualifier}" for word in kind.words for qualifier in kind.qualifiers]
    return list(kind.words)


class Colors:
    """The color of every type, wire and pin, from config.yaml."""

    def __init__(self, settings):
        self.settings = settings
        self.chosen = dict(settings.colors)   # type -> color, as the project wrote them
        self.picked = self.pick_defaults()    # type -> color, filled in by the tool

    def pick_defaults(self):
        """Every type of every family that the project left out, in order."""
        palette = self.settings.palette
        taken = set(self.chosen.values())
        picked = {}
        for kind_name, base in FAMILIES:
            kind = self.settings.kinds.get(kind_name)
            if kind is None or not kind.well_formed:
                continue
            for i, type_ in enumerate(kind_types(kind)):
                if type_ in self.chosen or is_hv(type_):
                    continue
                if kind_name == "can" and i == 1 and CAN_SECOND not in taken:
                    color = CAN_SECOND
                else:
                    color = first_free(base, palette, taken)
                picked[type_] = color
                taken.add(color)
        return picked

    def of_type(self, type_, tap=False):
        """The color of a type's wires, or None when it has no colored wire.
        A `tap` is a chain wire that only taps the chain: it gets the tap color
        where the palette has stripes."""
        if type_ in self.chosen:
            return self.chosen[type_]
        if is_hv(type_):
            return HV
        word, _ = split_type(type_)
        if self.is_word_of("chain", word):
            return TAP if tap and self.settings.palette != "solid" else CHAIN
        return self.picked.get(type_)

    def of_wire(self, own, type_, tap=False):
        """A wire's own color, else its type's."""
        if own is not None:
            return own
        return self.of_type(type_, tap)

    def is_picked(self, type_):
        """Whether the tool picked the type's color, rather than the project."""
        return type_ not in self.chosen and self.of_type(type_) is not None

    def is_word_of(self, kind_name, word):
        kind = self.settings.kinds.get(kind_name)
        return kind is not None and word in kind.words


def first_free(base, palette, taken):
    """The first color of a family nobody has taken: the base, then the base
    with each stripe. Without stripes, or with every one taken, the base."""
    family = [base]
    if palette != "solid":
        family += [f"{base}/{stripe}" for stripe in STRIPES if stripe != base]
    for color in family:
        if color not in taken:
            return color
    return base
