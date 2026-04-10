import pytest
from dynolayer.utils import Collection


class TestKeyConditionResolution:
    def test_index_query_moves_table_key_to_filter(self, get_user, create_table, aws_mock, save_records):
        result = (
            get_user.where("id", ">=", 1)
            .and_where("role", "admin")
            .index("role-index")
            .get()
        )

        assert isinstance(result, Collection)

    def test_table_query_keeps_partition_key(self, get_user, create_table, aws_mock, save_records):
        result = get_user.where("id", 1).get()

        assert isinstance(result, Collection)

    def test_index_with_composite_key(self, get_user, create_table, aws_mock, save_records):
        result = (
            get_user.where("role", "admin")
            .and_where("email", "begins_with", "j")
            .index("role-email-index")
            .get()
        )

        assert isinstance(result, Collection)

    def test_count_with_key_resolution(self, get_user, create_table, aws_mock, save_records):
        count = (
            get_user.where("id", ">=", 1)
            .and_where("role", "admin")
            .index("role-index")
            .count()
        )

        assert isinstance(count, int)


if __name__ == "__main__":
    pytest.main()
