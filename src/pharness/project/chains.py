"""The stretches of a chain, followed along their wires (CONFIG.md, Chains):
which boxes and devices each one reaches, and which of its wires carry the
loop from one node to the next and which only tap it."""


class Stretch:
    """One conductor of a chain, followed along its wires: the boxes and
    devices it reaches, and the wires joining them, each as the pair of places
    it joins. The pins of the conductor in one box are joined in that box."""

    def __init__(self, model, net, type_):
        self.pieces = {}       # box or device -> the place standing for its piece
        self.landed = set()    # boxes with a pin on it that is not `pass`
        self.devices = set()
        self.wires = set()     # frozenset({place, place})
        self.broken = False
        pins = [pin for pin in model.pins() if pin.is_on(net, type_)]
        wires = [(cable, wire) for cable in model.cables for wire in cable.wires
                 if wire.net == net and wire.type == type_]
        self.empty = not pins and not wires

        for pin in pins:
            self.add(pin.box)
            if pin.at != "pass":
                self.landed.add(pin.box)
            if pin.to is None:
                continue
            if model.is_device(pin.to):
                self.devices.add(pin.to)
            elif not model.is_box(pin.to) or not any(other.is_on(net, type_) for other in model.box(pin.to).pins()):
                self.broken = True
                continue
            self.join(pin.box, pin.to)
        for cable, wire in wires:
            from_, to = wire.ends
            if not all(model.is_device(end) and end in cable.ends for end in [from_, to]):
                self.broken = True   # wire-fields says so
                continue
            self.devices.update([from_, to])
            self.join(from_, to)

    def add(self, place):
        self.pieces.setdefault(place, place)

    def piece(self, place):
        self.add(place)
        while self.pieces[place] != place:
            place = self.pieces[place]
        return place

    def join(self, one, other):
        self.wires.add(frozenset([one, other]))
        self.pieces[self.piece(one)] = self.piece(other)

    def reaches(self, node):
        if node.box is not None:
            return node.box in self.landed
        return node.name in self.devices

    def joins(self, one, other):
        return self.piece(place(one)) == self.piece(place(other))

    def taps(self, ends):
        """The wires that only tap the stretch: every branch that ends
        somewhere other than `ends`, the places of its two nodes. What is left
        once those are cut off carries the loop."""
        wires = set(self.wires)
        while True:
            count = {}
            for wire in wires:
                for one in wire:
                    count[one] = count.get(one, 0) + 1
            loose = {one for one, n in count.items() if n == 1 and one not in ends}
            cut = {wire for wire in wires if wire & loose}
            if not cut:
                return self.wires - wires
            wires -= cut


def place(node):
    """Where a node is: its box, or the device it is."""
    return node.box if node.box is not None else node.name


def chain_taps(model):
    """The wires of every chain that only tap it, as (net, type) -> the pairs
    of places they join. Only a stretch with a next node has taps: what the
    last one leads to is not part of the chain. A stretch the checks could
    not follow has none."""
    taps = {}
    for chain, nodes in model.car.chains.items():
        for node, following in zip(nodes, nodes[1:]):
            if "out" not in node.data:
                continue
            stretch = Stretch(model, chain, node.type)
            if stretch.empty or stretch.broken or not stretch.joins(node, following):
                continue
            cut = stretch.taps({place(node), place(following)})
            if cut:
                taps[(chain, node.type)] = cut
    return taps
