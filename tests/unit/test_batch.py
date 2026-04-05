import pytest
from dynolayer.utils import Collection


class TestBatchCreate:
    def test_batch_create_multiple_records(self, get_user, create_table, aws_mock):
        users = get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
            {"id": 2, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"},
            {"id": 3, "first_name": "Bob", "email": "bob@mail.com", "role": "common"},
        ])

        assert len(users) == 3
        assert users[0].first_name == "John"
        assert users[1].first_name == "Jane"
        assert users[2].first_name == "Bob"

    def test_batch_create_validates_required_fields(self, get_user, create_table, aws_mock):
        from dynolayer.exceptions import ValidationException

        with pytest.raises(ValidationException):
            get_user.batch_create([
                {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
                {"id": 2},  # missing required fields
            ])

    def test_batch_create_filters_fillable(self, get_user, create_table, aws_mock):
        users = get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin", "secret": "ignored"},
        ])

        assert users[0].secret is None

    def test_batch_create_adds_timestamps(self, get_user, create_table, aws_mock):
        users = get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
        ])

        assert users[0].created_at is not None
        assert users[0].updated_at is not None


class TestBatchFind:
    def test_batch_find_returns_collection(self, get_user, create_table, aws_mock):
        get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
            {"id": 2, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"},
            {"id": 3, "first_name": "Bob", "email": "bob@mail.com", "role": "common"},
        ])

        result = get_user.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

        assert isinstance(result, Collection)
        assert result.count() == 3

    def test_batch_find_partial_keys(self, get_user, create_table, aws_mock):
        get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
        ])

        result = get_user.batch_find([{"id": 1}, {"id": 999}])

        assert result.count() == 1

    def test_batch_find_empty_keys(self, get_user, create_table, aws_mock):
        result = get_user.batch_find([])

        assert isinstance(result, Collection)
        assert result.count() == 0


class TestBatchDestroy:
    def test_batch_destroy_deletes_records(self, get_user, create_table, aws_mock):
        get_user.batch_create([
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
            {"id": 2, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"},
            {"id": 3, "first_name": "Bob", "email": "bob@mail.com", "role": "common"},
        ])

        get_user.batch_destroy([{"id": 1}, {"id": 2}])

        remaining = get_user.all().get(return_all=True)
        assert remaining.count() == 1
        assert remaining.first().id == 3
