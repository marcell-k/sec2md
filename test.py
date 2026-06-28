class Molecule:
    def __init__(self, name: str, charge: int, symbols, coordinates) -> None:
        self.name = name
        self.charge = charge
        self.symbols = symbols
        self.coordinates = coordinates

    @property
    def symbols(self):
        """The  property."""
        return self._symbols

    @symbols.setter
    def symbols(self, value):
        self._symbols = value
        self._num_atoms = len(value)
