class Deduplicator:
    def __init__(self):
        self._seen: set[str] = set()

    def first(self, key: str) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True
