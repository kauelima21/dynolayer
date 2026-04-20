import boto3
import pytest
from dynolayer.dynolayer import DynoLayer
from dynolayer.utils import Collection
from dynolayer.exceptions import ValidationException


@pytest.fixture
def create_table_with_sort_key(aws_mock):
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName="events",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "N"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def get_fast_user():
    class User(DynoLayer):
        raise_on_error = True

        def __init__(self):
            super().__init__(
                entity="users",
                required_fields=["first_name", "email", "role"],
                fillable=["id", "first_name", "last_name", "email", "role"],
                timestamps=False,
                partition_key="id",
            )
    return User


@pytest.fixture
def get_event():
    class Event(DynoLayer):
        raise_on_error = True

        def __init__(self):
            super().__init__(
                entity="events",
                fillable=["user_id", "timestamp", "type", "payload"],
                timestamps=False,
                partition_key="user_id",
                sort_key="timestamp",
            )
    return Event


@pytest.fixture
def get_default_pk_user():
    class User(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="users",
                required_fields=["first_name", "email", "role"],
                fillable=["id", "first_name", "last_name", "email", "role"],
                timestamps=False,
            )
    return User


class TestDefaultPartitionKey:
    def test_partition_key_defaults_to_id(self, get_default_pk_user):
        user = get_default_pk_user()
        assert user._hash_key == "id"
        assert user._partition_keys == ["id"]

    def test_create_with_default_partition_key(self, get_default_pk_user, create_table, aws_mock):
        user = get_default_pk_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        assert user.id == 1

    def test_get_item_with_default_partition_key(self, get_default_pk_user, create_table, aws_mock):
        get_default_pk_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user = get_default_pk_user.get_item({"id": 1})
        assert user.first_name == "John"

    def test_save_with_default_partition_key(self, get_default_pk_user, create_table, aws_mock):
        get_default_pk_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user = get_default_pk_user.get_item({"id": 1})
        user.first_name = "Jane"
        user.save()
        assert get_default_pk_user.get_item({"id": 1}).first_name == "Jane"

    def test_delete_with_default_partition_key(self, get_default_pk_user, create_table, aws_mock):
        get_default_pk_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        get_default_pk_user.delete({"id": 1})
        assert get_default_pk_user.get_item({"id": 1}) is None


class TestDeclaredPartitionKey:
    def test_create_without_describe_table(self, get_fast_user, create_table, aws_mock):
        user = get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        assert user.id == 1
        assert user.first_name == "John"

    def test_find_without_describe_table(self, get_fast_user, create_table, aws_mock):
        get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user = get_fast_user.get_item({"id": 1})
        assert user.first_name == "John"

    def test_save_without_describe_table(self, get_fast_user, create_table, aws_mock):
        get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user = get_fast_user.get_item({"id": 1})
        user.first_name = "Jane"
        user.save()
        assert get_fast_user.get_item({"id": 1}).first_name == "Jane"

    def test_delete_without_describe_table(self, get_fast_user, create_table, aws_mock):
        get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        get_fast_user.delete({"id": 1})
        assert get_fast_user.get_item({"id": 1}) is None

    def test_destroy_without_describe_table(self, get_fast_user, create_table, aws_mock):
        user = get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        user.destroy()
        assert get_fast_user.get_item({"id": 1}) is None

    def test_validate_key_dict(self, get_fast_user, create_table, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_fast_user.get_item({})

    def test_index_query_lazy_loads_indexes(self, get_fast_user, create_table, aws_mock):
        get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        result = get_fast_user.where("role", "admin").index("role-index").get(all=True)
        assert isinstance(result, Collection)
        assert result.count() >= 1

    def test_all_scan_without_describe_table(self, get_fast_user, create_table, aws_mock):
        get_fast_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        result = get_fast_user.all().get(all=True, paginate=True)
        assert result.count() == 1


class TestDeclaredCompositeKey:
    def test_create_with_composite_key(self, get_event, create_table_with_sort_key, aws_mock):
        event = get_event.create({"user_id": "u1", "timestamp": 1000, "type": "login", "payload": "ok"})
        assert event.user_id == "u1"
        assert event.timestamp == 1000

    def test_find_with_composite_key(self, get_event, create_table_with_sort_key, aws_mock):
        get_event.create({"user_id": "u1", "timestamp": 1000, "type": "login", "payload": "ok"})
        event = get_event.get_item({"user_id": "u1", "timestamp": 1000})
        assert event.type == "login"

    def test_find_missing_sort_key_raises(self, get_event, create_table_with_sort_key, aws_mock):
        with pytest.raises(ValidationException, match="Missing primary key"):
            get_event.get_item({"user_id": "u1"})

    def test_save_with_composite_key(self, get_event, create_table_with_sort_key, aws_mock):
        get_event.create({"user_id": "u1", "timestamp": 1000, "type": "login", "payload": "ok"})
        event = get_event.get_item({"user_id": "u1", "timestamp": 1000})
        event.payload = "updated"
        event.save()
        assert get_event.get_item({"user_id": "u1", "timestamp": 1000}).payload == "updated"


if __name__ == "__main__":
    pytest.main()
