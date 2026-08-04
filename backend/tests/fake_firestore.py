"""In-memory stand-in for the Firestore client.

Enough of the API surface for `FirestoreStore`: nested collections, document
get/set/update/delete, and equality/array_contains queries. Values are deep
copied on the way in and out so a caller mutating a returned dict cannot reach
back into the store — real Firestore has the same property, and a fake that
doesn't will hide aliasing bugs.

Not a Firestore emulator. It does not model transactions, indexes, or field
paths with dots, none of which `FirestoreStore` uses.
"""
from __future__ import annotations

import copy
from typing import Any, Iterator, Optional


class _Snapshot:
    def __init__(self, doc_id: str, data: Optional[dict]):
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[dict]:
        return copy.deepcopy(self._data) if self._data is not None else None


class _Node:
    """A document: its own fields plus any sub-collections hanging off it."""

    def __init__(self):
        self.data: Optional[dict] = None
        self.collections: dict[str, dict[str, "_Node"]] = {}


class _DocumentRef:
    def __init__(self, node: _Node, doc_id: str):
        self._node = node
        self.id = doc_id

    def get(self) -> _Snapshot:
        return _Snapshot(self.id, self._node.data)

    def set(self, data: dict) -> None:
        self._node.data = copy.deepcopy(data)

    def update(self, patch: dict) -> None:
        if self._node.data is None:
            raise KeyError(f"No document to update: {self.id}")
        self._node.data.update(copy.deepcopy(patch))

    def delete(self) -> None:
        self._node.data = None

    def collection(self, name: str) -> "_CollectionRef":
        return _CollectionRef(self._node.collections.setdefault(name, {}))


class _Query:
    def __init__(self, docs: dict[str, _Node], filters: list[tuple[str, str, Any]]):
        self._docs = docs
        self._filters = filters

    def where(self, field: str, op: str, value: Any) -> "_Query":
        return _Query(self._docs, self._filters + [(field, op, value)])

    def _matches(self, data: dict) -> bool:
        for field, op, value in self._filters:
            actual = data.get(field)
            if op == "==":
                if actual != value:
                    return False
            elif op == "array_contains":
                if not isinstance(actual, (list, tuple)) or value not in actual:
                    return False
            else:
                raise NotImplementedError(f"Unsupported operator: {op}")
        return True

    def stream(self) -> Iterator[_Snapshot]:
        for doc_id, node in list(self._docs.items()):
            if node.data is not None and self._matches(node.data):
                yield _Snapshot(doc_id, node.data)


class _CollectionRef(_Query):
    def __init__(self, docs: dict[str, _Node]):
        super().__init__(docs, [])

    def document(self, doc_id: str) -> _DocumentRef:
        node = self._docs.setdefault(doc_id, _Node())
        return _DocumentRef(node, doc_id)


class FakeFirestore:
    """Root client. `client.collection("vessels").document(id)...`"""

    def __init__(self):
        self._root: dict[str, dict[str, _Node]] = {}

    def collection(self, name: str) -> _CollectionRef:
        return _CollectionRef(self._root.setdefault(name, {}))
