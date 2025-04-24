import pytest


class TestRetrieveRecords:
    # This method executes a scan in all table
    def test_with_all_method(self, get_user, create_table, aws_mock, save_records):
        response = get_user.all()
        assert len(response) == 20

    # Find a record with the primary key
    def test_with_find_method(self, get_user, create_table, aws_mock):
        get_user.create({
            "id": 999,
            "first_name": "Joanne",
            "email": "joanne@email.com",
            "role": "admin",
        })
        user = get_user.find({"id": 999, "role": "admin"})

        assert isinstance(user, get_user)
        assert user.id == 999


class TestQueryBuilder:
    def test_with_where_method(self, get_user, create_table, aws_mock, save_records):
        get_user.create({
            "id": 100,
            "role": "moderator",
            "first_name": "Jack",
            "email": "jack@mail.com",
            "stars": 4
        })
        moderators_with_more_than_3_stars = (get_user.where("stars", ">", 2)
                                             .and_where("stars", "<", 5)
                                             .and_where("role", "moderator")
                                             .index("role-index")
                                             .fetch())

        assert isinstance(moderators_with_more_than_3_stars, list)
        assert moderators_with_more_than_3_stars[0]["role"] == "moderator"
        assert moderators_with_more_than_3_stars[0]["stars"] > 2
        assert moderators_with_more_than_3_stars[0]["stars"] < 5

    def test_with_or_where_method(self, get_user, create_table, aws_mock, save_records):
        get_user.create({
            "id": 100,
            "role": "moderator",
            "first_name": "Jack",
            "email": "jack@mail.com",
            "stars": 4.5
        })
        user_with_stars_between_2_and_3 = (get_user.where("stars", ">=", 2)
                                           .and_where("stars", "<=", 3)
                                           .or_where("email", "jack@mail.com")
                                           .get())

        assert isinstance(user_with_stars_between_2_and_3, list)
        assert user_with_stars_between_2_and_3[0]["stars"] >= 2

    def test_with_where_between_method(self, get_user, create_table, aws_mock, save_records):
        from datetime import datetime, timedelta, timezone

        get_user.create({
            "id": 123,
            "role": "admin",
            "first_name": "Luke",
            "email": "luke@mail.com",
        })
        timestamp_yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        timestamp_today = int(datetime.now(timezone.utc).timestamp())
        admins_created_between_yesterday_and_today = (get_user.where("role", "admin")
                        .where_between("created_at", timestamp_yesterday, timestamp_today)
                        .index("role-index")
                        .fetch())

        assert isinstance(admins_created_between_yesterday_and_today, list)
        assert len(admins_created_between_yesterday_and_today) == 1
        assert admins_created_between_yesterday_and_today[0]["first_name"] == "Luke"

    def test_with_where_in_method(self, get_user, create_table, aws_mock, save_records):
        admins = (get_user.where("role", "admin")
                        .where_in("stars", [2, 3, 5])
                        .index("role-index")
                        .fetch())

        assert isinstance(admins, list)

    def test_with_where_not_method(self, get_user, create_table, aws_mock, save_records):
        admins = get_user().where_not("stars", "in", [3, 4, 5]).get()

        assert isinstance(admins, list)

    def test_with_begins_with(self, get_user, create_table, aws_mock, save_records):
        get_user.create({
            "id": 934,
            "role": "admin",
            "first_name": "Harry",
            "email": "potter.harry@mail.com",
        })
        potter_heads = (get_user.where("role", "admin")
         .and_where("email", "begins_with","potter")
         .index("role-email-index")
         .fetch())

        assert isinstance(potter_heads, list)
        assert potter_heads[0]["first_name"] == "Harry"


if __name__ == "__main__":
    pytest.main()
