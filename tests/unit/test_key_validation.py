import pytest
from dynolayer.exceptions import ValidationException, QueryException


class TestPrimaryKeyValidation:
    def test_get_item_with_missing_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.get_item({})

    def test_get_item_with_valid_key_passes(self, get_user, create_table, aws_mock, save_records):
        user = get_user.get_item({"id": 1})
        assert user is not None

    def test_delete_with_missing_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.delete({})

    def test_delete_with_valid_key_passes(self, get_user, create_table, aws_mock, save_records):
        response = get_user.delete({"id": 1})
        assert response

    def test_find_or_fail_with_missing_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.find_or_fail({})

    def test_batch_find_with_missing_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.batch_find([{"id": 1}, {}])

    def test_batch_destroy_with_missing_key_raises(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_user.batch_destroy([{"id": 1}, {}])


class TestIndexValidation:
    def test_query_with_invalid_index_raises(self, get_user, create_table, aws_mock, save_records):
        with pytest.raises(QueryException, match="does not exist"):
            get_user.where("role", "admin").index("nonexistent-index").get()

    def test_query_with_index_missing_partition_key_raises(self, get_user, create_table, aws_mock, save_records):
        with pytest.raises(QueryException, match="requires partition key"):
            get_user.where("id", 1).index("role-index").get()

    def test_query_with_valid_index_passes(self, get_user, create_table, aws_mock, save_records):
        result = get_user.where("role", "admin").index("role-index").get()
        assert result is not None

    def test_count_with_invalid_index_raises(self, get_user, create_table, aws_mock, save_records):
        with pytest.raises(QueryException, match="does not exist"):
            get_user.where("role", "admin").index("nonexistent-index").count()

    def test_count_with_valid_index_passes(self, get_user, create_table, aws_mock, save_records):
        count = get_user.where("role", "admin").index("role-index").count()
        assert isinstance(count, int)


if __name__ == "__main__":
    pytest.main()
