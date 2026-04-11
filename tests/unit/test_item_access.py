import pytest


class TestGetItem:
    def test_returns_field_value(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        assert user["first_name"] == "Ana"

    def test_raises_key_error_for_missing_key(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        with pytest.raises(KeyError):
            _ = user["nonexistent"]

    def test_accessing_field_that_collides_with_method(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        result = user.data()
        assert "data" not in result

        user._data["data"] = "campo real"
        assert user["data"] == "campo real"
        assert callable(user.data)


class TestSetItem:
    def test_sets_field_value(self, get_user):
        user = get_user()
        user["first_name"] = "Carlos"
        assert user._data["first_name"] == "Carlos"

    def test_overwrites_existing_field(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        user["first_name"] = "Bia"
        assert user["first_name"] == "Bia"


class TestContains:
    def test_returns_true_for_existing_key(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        assert "first_name" in user

    def test_returns_false_for_missing_key(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        assert "nonexistent" not in user


class TestDelItem:
    def test_deletes_field(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        del user["first_name"]
        assert "first_name" not in user

    def test_raises_key_error_for_missing_key(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1, "first_name": "Ana", "email": "ana@mail.com", "role": "admin",
        })
        with pytest.raises(KeyError):
            del user["nonexistent"]
