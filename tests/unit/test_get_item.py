import pytest
from dynolayer.utils import Collection
from dynolayer.exceptions import ValidationException, RecordNotFoundException


class TestGetItem:
    def test_get_item_returns_record(self, get_user, create_table, aws_mock, save_records):
        user = get_user.get_item({"id": 1})
        assert user is not None
        assert user.id == 1

    def test_get_item_returns_none_for_missing(self, get_user, create_table, aws_mock):
        user = get_user.get_item({"id": 999})
        assert user is None

    def test_get_item_with_attributes(self, get_user, create_table, aws_mock, save_records):
        user = get_user.get_item({"id": 1}, attributes=["first_name", "email"])
        assert user is not None
        assert user.first_name is not None

    def test_get_item_with_empty_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.get_item({})


class TestFindOrFailUsesGetItem:
    def test_find_or_fail_returns_record(self, get_user, create_table, aws_mock, save_records):
        user = get_user.find_or_fail({"id": 1})
        assert user is not None
        assert user.id == 1

    def test_find_or_fail_raises_when_not_found(self, get_user, create_table, aws_mock):
        with pytest.raises(RecordNotFoundException, match="Record not found"):
            get_user.find_or_fail({"id": 999})


class TestFindInstanceMethod:
    def test_find_without_args_scan_all(self, get_user, create_table, aws_mock, save_records):
        result = get_user().find().fetch(True)
        assert isinstance(result, Collection)
        assert result.count() == 20

    def test_find_with_partition_key(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 500,
            "role": "admin",
            "first_name": "FindTest",
            "email": "findtest@mail.com",
        })

        result = get_user().find("role = :r", r="admin").index("role-index").fetch(True)
        assert isinstance(result, Collection)
        assert result.count() >= 1

    def test_find_with_multiple_conditions(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 600,
            "role": "admin",
            "first_name": "MultiTest",
            "email": "multi@mail.com",
            "stars": 5,
        })

        result = (
            get_user()
            .find("role = :r AND stars = :s", r="admin", s=5)
            .index("role-index")
            .fetch(True)
        )
        assert isinstance(result, Collection)

    def test_find_with_begins_with(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 700,
            "role": "admin",
            "first_name": "BeginsTest",
            "email": "begins.test@mail.com",
        })

        result = (
            get_user()
            .find("role = :r AND email begins_with :prefix", r="admin", prefix="begins")
            .index("role-email-index")
            .fetch(True)
        )
        assert isinstance(result, Collection)
        assert result.count() >= 1
        assert result.first().first_name == "BeginsTest"

    def test_find_with_between(self, get_user, create_table, aws_mock, save_records):
        from datetime import datetime, timedelta, timezone

        get_user().create({
            "id": 800,
            "role": "admin",
            "first_name": "BetweenTest",
            "email": "between@mail.com",
        })

        ts_yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        ts_today = int(datetime.now(timezone.utc).timestamp())

        result = (
            get_user()
            .find("role = :r AND created_at between :start and :end", r="admin", start=ts_yesterday, end=ts_today)
            .index("role-index")
            .fetch(True)
        )
        assert isinstance(result, Collection)
        assert result.count() >= 1

    def test_find_scan_with_filter(self, get_user, create_table, aws_mock, save_records):
        result = get_user().find("stars = :s", s=3).force_scan().get(return_all=True)
        assert isinstance(result, Collection)

    def test_find_with_chaining(self, get_user, create_table, aws_mock, save_records):
        result = (
            get_user()
            .find("role = :r", r="admin")
            .index("role-index")
            .limit(5)
            .fetch()
        )
        assert isinstance(result, Collection)
        assert result.count() <= 5


if __name__ == "__main__":
    pytest.main()
