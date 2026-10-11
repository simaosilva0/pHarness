"""The stretches of a chain, followed along their wires (CONFIG.md, Chains):
which boxes and devices each one reaches."""


class Stretch:
    """One conductor of a chain, followed along its wires: the boxes and
    devices it reaches. The pins of the conductor in one box are joined in
    that box."""

    def __init__(self, model, net, type_):
        self.pieces = {}       # box or device -> the place standing for its piece
        self.landed = set()    # boxes with a pin on it that is not `pass`
        self.devices = set()
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
        self.pieces[self.piece(one)] = self.piece(other)

    def reaches(self, node):
        if node.box is not None:
            return node.box in self.landed
        return node.name in self.devices

    def joins(self, one, other):
        return self.piece(place(one)) == self.piece(place(other))


def place(node):
    """Where a node is: its box, or the device it is."""
    return node.box if node.box is not None else node.name
