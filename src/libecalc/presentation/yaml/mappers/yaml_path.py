Key = str | int


class YamlPath:
    def __init__(self, keys: tuple[Key, ...] = None):
        self._keys = keys or ()

    @property
    def keys(self) -> tuple[Key, ...]:
        return self._keys

    def append(self, key: Key):
        return YamlPath((*self._keys, key))

    def __eq__(self, other) -> bool:
        if isinstance(other, YamlPath):
            return self.keys == other.keys
        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        return self.keys.__hash__()
