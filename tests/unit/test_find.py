import pytest
from dynolayer.utils import Collection


class TestRetrieveRecords:
    def test_with_all_method(self, get_user, create_table, aws_mock, save_records):
        response = get_user().all()
        assert isinstance(response, Collection)
        assert response.count() == 20


class TestQueryBuilder:
    def test_with_where_method(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 100,
            "role": "moderator",
            "first_name": "Jack",
            "email": "jack@mail.com",
            "stars": 4
        })

        result = (
            get_user().where("stars", ">", 2)
            .and_where("stars", "<", 5)
            .and_where("role", "moderator")
            .index("role-index")
            .fetch()
        )

        assert isinstance(result, Collection)
        user = result.first()

        assert user.role == "moderator"
        assert user.stars > 2
        assert user.stars < 5

    def test_with_or_where_method(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 100,
            "role": "moderator",
            "first_name": "Jack",
            "email": "jack@mail.com",
            "stars": 4.5
        })

        result = (
            get_user().where("stars", ">=", 2)
            .and_where("stars", "<=", 3)
            .or_where("email", "jack@mail.com")
            .force_scan()
            .get()
        )

        assert isinstance(result, Collection)
        assert result.first().stars >= 2

    def test_with_where_between_method(self, get_user, create_table, aws_mock, save_records):
        from datetime import datetime, timedelta, timezone

        get_user().create({
            "id": 123,
            "role": "admin",
            "first_name": "Luke",
            "email": "luke@mail.com",
        })

        ts_yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        ts_today = int(datetime.now(timezone.utc).timestamp())

        result = (
            get_user().where("role", "admin")
            .where_between("created_at", ts_yesterday, ts_today)
            .index("role-index")
            .fetch()
        )

        assert isinstance(result, Collection)
        assert result.count() == 1
        assert result.first().first_name == "Luke"

    def test_with_where_in_method(self, get_user, create_table, aws_mock, save_records):
        result = (
            get_user().where("role", "admin")
            .where_in("stars", [2, 3, 5])
            .index("role-index")
            .fetch()
        )

        assert isinstance(result, Collection)

    def test_with_where_not_method(self, get_user, create_table, aws_mock, save_records):
        result = get_user().where_not("stars", "in", [3, 4, 5]).get()
        assert isinstance(result, Collection)

    def test_with_begins_with(self, get_user, create_table, aws_mock, save_records):
        get_user().create({
            "id": 934,
            "role": "admin",
            "first_name": "Harry",
            "email": "potter.harry@mail.com",
        })

        result = (
            get_user().where("role", "admin")
            .and_where("email", "begins_with", "potter")
            .index("role-email-index")
            .fetch()
        )

        assert isinstance(result, Collection)
        assert result.first().first_name == "Harry"