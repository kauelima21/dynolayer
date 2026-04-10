import boto3
import pytest
from dynolayer.dynolayer import DynoLayer


@pytest.fixture
def create_orders_table(aws_mock):
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName="orders",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "N"}],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def get_order():
    class Order(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="orders",
                required_fields=["total"],
                fillable=["id", "total", "status"],
                timestamps=False,
            )
    return Order


class TestTransactWrite:
    def test_transact_write_put_and_delete(self, get_user, get_order, create_table, create_orders_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        DynoLayer.transact_write([
            get_user.prepare_put({"id": 2, "first_name": "Jane", "email": "jane@mail.com", "role": "admin"}),
            get_order.prepare_put({"id": 100, "total": 50, "status": "pending"}),
            get_user.prepare_delete({"id": 1}),
        ])

        assert get_user.find({"id": 1}) is None
        assert get_user.find({"id": 2}).first_name == "Jane"
        assert get_order.find({"id": 100}).total == 50

    def test_transact_write_with_update(self, get_user, create_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        DynoLayer.transact_write([
            get_user.prepare_update({"id": 1}, {"first_name": "Jane"}),
        ])

        user = get_user.find({"id": 1})
        assert user.first_name == "Jane"


class TestTransactGet:
    def test_transact_get_multiple_models(self, get_user, get_order, create_table, create_orders_table, aws_mock):
        get_user.create({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})
        get_order.create({"id": 100, "total": 50, "status": "pending"})

        results = DynoLayer.transact_get([
            (get_user, {"id": 1}),
            (get_order, {"id": 100}),
        ])

        assert len(results) == 2
        assert results[0].first_name == "John"
        assert results[1].total == 50

    def test_transact_get_missing_record(self, get_user, create_table, aws_mock):
        results = DynoLayer.transact_get([
            (get_user, {"id": 999}),
        ])

        assert results[0] is None


class TestPreparePut:
    def test_prepare_put_applies_timestamps(self, get_user, create_table, aws_mock):
        result = get_user.prepare_put({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin"})

        assert result["Put"]["TableName"] == "users"
        assert result["Put"]["Item"]["first_name"] == "John"
        assert "created_at" in result["Put"]["Item"]
        assert "updated_at" in result["Put"]["Item"]

    def test_prepare_put_filters_fillable(self, get_user, create_table, aws_mock):
        result = get_user.prepare_put({"id": 1, "first_name": "John", "email": "john@mail.com", "role": "admin", "secret": "hidden"})

        assert "secret" not in result["Put"]["Item"]


if __name__ == "__main__":
    pytest.main()
