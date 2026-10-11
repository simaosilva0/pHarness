"""Nets and types (CONFIG.md: Nets, Types, Buses, Ethernet, Chains), and
any name in its style (CONFIG.md, Styles)."""

from ..project.labels import net_separator, split_type
from ..project.settings import BUS_KINDS, KINDS_WITHOUT_WORDS
from ..project.styles import in_net_case, in_style


def check_style(report, rule, name, style, at, what):
    """A name written in its style. Nothing is checked when the style itself was
    set wrong (None): there is no style to check against."""
    if style is None:
        return True
    return report.check(rule, in_style(name, style), at, f"{what} {name} is not {style}")


class NetChecks:
    """Checks a net or a type wherever it is written: on a pin, or as the name
    of a bus, link or chain."""

    def __init__(self, model, report):
        settings = model.settings
        self.model = model
        self.report = report
        self.style = settings.style["net"]   # None when set wrong: nets are not checked
        self.separator = net_separator(settings)
        self.sides = settings.sides
        self.kinds = settings.kinds
        self.labels = self.words_a_net_may_not_end_in()

    def words_a_net_may_not_end_in(self):
        """Every label, qualifier and chain out: the type already says them."""
        words = set()
        for kind in self.kinds.values():
            if kind.name in KINDS_WITHOUT_WORDS:
                continue   # a label or qualifier there is a kind-form mistake, not a word
            if kind.label is not None:
                words.add(str(kind.label))
            words.update(kind.qualifiers)
        for node in self.model.nodes():
            words.add(node.out)
        return words

    def words(self, net):
        return net.split(self.separator)

    # --- nets ----------------------------------------------------------------

    def check_net(self, net, at):
        """net-style, net-letter, net-side-first, net-thing, net-no-label,
        and bus-net or eth-net when it starts like one."""
        if self.style is None:
            return
        report = self.report
        if not report.check("net-style", in_style(net, self.style), at, f"net {net} is not {self.style}"):
            return

        words = self.words(net)
        report.check("net-letter", net[0].isalpha(), at, f"net {net} does not start with a letter")
        report.check("net-side-first", self.side_only_first(words), at, f"net {net} has a side after its first word")
        report.check("net-thing", self.has_thing(words), at, f"net {net} has no word besides its side and index")

        last = words[-1]
        ends_in_label = last in self.labels and not last.isdigit()
        report.check("net-no-label", not ends_in_label, at, f"net {net} ends in {last}, which its type already says")

        first = words[0]
        if first.lower() in BUS_KINDS:
            report.check("bus-net", net in self.model.car.buses, at, f"net {net} starts with {first} but is not a bus")
        if first == in_net_case("ETH", self.style):
            report.check("eth-net", net in self.model.car.links, at, f"net {net} starts with {first} but is not a link")

    def side_only_first(self, words):
        later_words = words[1:]
        return not any(word in self.sides for word in later_words)

    def has_thing(self, words):
        """Whether a word is left once the leading side and the trailing index are taken off."""
        thing = list(words)
        if thing and thing[0] in self.sides:
            thing = thing[1:]
        if len(thing) > 1 and thing[-1].isdigit():
            thing = thing[:-1]
        if not thing:
            return False
        only_an_index = len(thing) == 1 and thing[0].isdigit()
        return not only_an_index

    # --- types ---------------------------------------------------------------

    def check_type(self, net, type_, at):
        """The type of one pin, given its net (None when it has none): chain-type,
        bus-type, eth-type, pin-type."""
        report = self.report
        word, qualifier = split_type(type_)
        what = f"{net or '(no net)'} {type_}"
        car = self.model.car

        if self.is_word_of("chain", word) or net in car.chains:
            outs = self.model.chain_outs(net)
            ok = net in car.chains and self.is_word_of("chain", word) and qualifier in outs
            report.check("chain-type", ok, at, f"{what}: a chain pin is chain:<out> of its chain, only on a chain")
            return

        bus_kinds = [kind for kind in BUS_KINDS if self.is_word_of(kind, word)]
        if bus_kinds or net in car.buses:
            ok = net in car.buses and self.is_word_of(self.bus_kind(net), word)
            report.check("bus-type", ok, at, f"{what}: a bus pin has its bus's type, only on its bus")

        if self.is_word_of("ethernet", word) or net in car.links:
            ok = net in car.links and self.is_word_of("ethernet", word)
            report.check("eth-type", ok, at, f"{what}: an ethernet pin is only on a link")

        report.check("pin-type", self.fits_a_kind(word, qualifier), at, f"{what} is not a type of any kind")

    def is_word_of(self, kind_name, word):
        kind = self.kinds.get(kind_name)
        return kind is not None and word in kind.words

    def bus_kind(self, bus):
        """The kind of a bus: its first word, `CAN_E` -> can."""
        return self.words(bus)[0].lower()

    def fits_a_kind(self, word, qualifier):
        """A word of a label kind alone, or a word of a qualifier kind with one of
        its qualifiers. Chain types are checked on their own."""
        for kind in self.kinds.values():
            if kind.name == "chain" or word not in kind.words:
                continue
            if not kind.well_formed:
                return True   # its form is reported on the kind; no guessing what was meant
            if kind.qualifiers and qualifier in kind.qualifiers:
                return True
            if not kind.qualifiers and qualifier is None:
                return True
        return False
