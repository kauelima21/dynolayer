import pytest
from boto3.dynamodb.conditions import Attr
from dynolayer.exceptions import ConditionalCheckException


class TestUniqueCreate:
    def test_create_unique_succeeds_for_new_record(self, get_user, create_table, aws_mock):
        user = get_user.create(
            {"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"},
            unique=True,
        )
        assert user.id == 1

    def test_create_unique_fails_for_existing_record(self, get_user, create_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        with pytest.raises(ConditionalCheckException, match="already exists"):
            get_user.create(
                {"id": 1, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"},
                unique=True,
            )

    def test_create_without_unique_overwrites(self, get_user, create_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user = get_user.create({"id": 1, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"})
        assert user.first_name == "Jane"


class TestConditionalSave:
    def test_save_with_condition_succeeds(self, get_user, create_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        user = get_user.get_item({"id": 1})
        user.first_name = "Jane"
        result = user.save(condition=Attr("role").eq("admin"))
        assert result is True

    def test_save_with_condition_fails(self, get_user, create_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        user = get_user.get_item({"id": 1})
        user.first_name = "Jane"
        with pytest.raises(ConditionalCheckException):
            user.save(condition=Attr("role").eq("moderator"))


if __name__ == "__main__":
    pytest.main()
