import pytest


class TestRemoveRecords:
    def test_with_destroy_method(self, get_user, create_table, aws_mock, save_records):
        user = get_user.find({"id": 5})
        assert isinstance(user.first_name, str)
        assert user.destroy()

    def test_with_delete_method(self, get_user, create_table, aws_mock, save_records):
        response = get_user.delete({"id": 5})
        assert response


if __name__ == "__main__":
    pytest.main()
