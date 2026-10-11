"""Types and the wire labels built from them (CONFIG.md: Types, Labels)."""

from .styles import DEFAULT_STYLE, STYLES


def split_type(type_):
    """`power:24V` -> ("power", "24V"); `ground` -> ("ground", None)."""
    word, colon, qualifier = str(type_).partition(":")
    if not colon:
        return word, None
    return word, qualifier


def net_separator(settings):
    """The separator between the words of a net, in the project's net style."""
    style = settings.style["net"] or DEFAULT_STYLE["net"]
    return STYLES[style].separator


def wire_label(settings, net, type_):
    """`<net>_<label>`: the kind's label, or the type's qualifier (CONFIG.md,
    Labels). None when the type gives neither."""
    separator = net_separator(settings)
    word, qualifier = split_type(type_)
    if qualifier is not None:
        return net + separator + qualifier
    for kind in settings.kinds.values():
        if word in kind.words and kind.label is not None:
            return net + separator + str(kind.label)
    return None
