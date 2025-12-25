import pytest
from dynolayer.utils import Collection


class FakeModel:
    def __init__(self, data):
        self._data = data

    def data(self):
        return self._data

    def __getattr__(self, item):
        return self._data.get(item)


def test_collection_creation():
    items = [
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
    ]

    collection = Collection(items)

    assert collection is not None


def test_collection_is_iterable():
    items = [
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
    ]

    collection = Collection(items)

    ids = [item.id for item in collection]

    assert ids == [1, 2]


def test_collection_first():
    items = [
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
    ]

    collection = Collection(items)

    first = collection.first()

    assert first.id == 1


def test_collection_first_empty():
    collection = Collection([])

    assert collection.first() is None


def test_collection_count():
    collection = Collection([
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
        FakeModel({"id": 3}),
    ])

    assert collection.count() == 3


def test_collection_len():
    collection = Collection([
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
    ])

    assert len(collection) == 2


def test_collection_pluck():
    collection = Collection([
        FakeModel({"id": 1, "email": "a@mail.com"}),
        FakeModel({"id": 2, "email": "b@mail.com"}),
    ])

    emails = collection.pluck("email")

    assert emails == ["a@mail.com", "b@mail.com"]


def test_collection_pluck_missing_key():
    collection = Collection([
        FakeModel({"id": 1}),
        FakeModel({"id": 2}),
    ])

    values = collection.pluck("email")

    assert values == [None, None]


def test_collection_to_list():
    collection = Collection([
        FakeModel({"id": 1, "name": "John"}),
        FakeModel({"id": 2, "name": "Jane"}),
    ])

    result = collection.to_list()

    assert result == [
        {"id": 1, "name": "John"},
        {"id": 2, "name": "Jane"},
    ]


def test_collection_common_usage_pattern():
    collection = Collection([
        FakeModel({"id": 1, "role": "admin", "email": "a@mail.com"}),
        FakeModel({"id": 2, "role": "admin", "email": "b@mail.com"}),
    ])

    assert collection.count() == 2
    assert collection.first().role == "admin"
    assert collection.pluck("email") == ["a@mail.com", "b@mail.com"]


if __name__ == "__main__":
    pytest.main()
