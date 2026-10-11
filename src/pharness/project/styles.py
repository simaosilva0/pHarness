"""How names are written (CONFIG.md, Styles)."""

import re
from typing import NamedTuple

# One word of each case. A title word is a capital and then lower case letters
# and digits, all capitals, all capitals and a plural `s` (NTCs), or digits.
UPPER_WORD = r"[A-Z0-9]+"
LOWER_WORD = r"[a-z0-9]+"
TITLE_WORD = r"(?:[A-Z][a-z0-9]*|[A-Z0-9]+s?|[0-9]+)"


class Style(NamedTuple):
    word: str          # the pattern of one word
    separator: str     # between words; "" when the name is one word


STYLES = {
    "upper_snake": Style(UPPER_WORD, "_"),
    "snake": Style(LOWER_WORD, "_"),
    "upper_kebab": Style(UPPER_WORD, "-"),
    "kebab": Style(LOWER_WORD, "-"),
    "title": Style(TITLE_WORD, " "),
    "pascal": Style(r"[A-Z][a-zA-Z0-9]*", ""),
    "camel": Style(r"[a-z][a-zA-Z0-9]*", ""),
}

# A net needs a separator to tell its side and index from the rest.
NET_STYLES = ["upper_snake", "snake", "upper_kebab", "kebab"]

DEFAULT_STYLE = {
    "net": "upper_snake",
    "box": "title",
    "connector": "title",
    "device": "title",
    "board": "kebab",
    "cable": "title",
}


def in_style(name, style):
    """Whether a name is written in a style."""
    if not isinstance(name, str):
        return False
    word, separator = STYLES[style]
    if separator:
        pattern = f"{word}(?:{re.escape(separator)}{word})*"
    else:
        pattern = word
    return re.fullmatch(pattern, name) is not None


def is_upper(net_style):
    return net_style.startswith("upper")


def is_net_word(word, net_style):
    """Whether a word fits in a net of this style: one word, in its case.
    Sides, labels, qualifiers and chain outs all end up in nets and wire labels."""
    if is_upper(net_style):
        pattern = UPPER_WORD
    else:
        pattern = LOWER_WORD
    return re.fullmatch(pattern, str(word)) is not None


def in_net_case(word, net_style):
    """A fixed word such as CAN or ETH, written in the nets' case."""
    if is_upper(net_style):
        return word.upper()
    return word.lower()
