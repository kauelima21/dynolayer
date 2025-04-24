import pytest


class TestCreateRecord:
    def test_with_create_method(self, get_user, create_table, aws_mock):
        input_user_data = {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@mail.com",
            "role": "common",
            "stars": 3.5,
            "stats": {
                "wins": 32,
                "loss": 7,
            },
            "phones": [
                "11 91234-5678",
                "10 95678-1234",
            ],
            "this_will_not_be_added": "it will be skipped"
        }

        created_user = get_user.create(input_user_data)
        assert created_user.id == 1

    def test_with_save_method(self, get_user, create_table, aws_mock):
        user = get_user()
        user.id = 100
        user.first_name = "Joanne"
        user.email = "joanne@email.com"
        user.role = "admin"

        assert user.save()


class TestUpdateRecord:
    def test_with_save_method(self, get_user, create_table, aws_mock):
        user_to_update = get_user.create({
            "id": 999,
            "first_name": "Joanne",
            "email": "joanne@email.com",
            "role": "admin",
        })

        user_to_update.first_name = "John"
        user_to_update.save()

        assert user_to_update.id == 999
        assert user_to_update.first_name == "John"


if __name__ == "__main__":
    pytest.main()
