Key = str | int


class YamlPath:
    def __init__(self, keys: tuple[Key, ...] = None):
        self._keys = keys or ()

    @property
    def keys(self) -> tuple[Key, ...]:
        return self._keys

    def append(self, key: Key):
        return YamlPath((*self._keys, key))
