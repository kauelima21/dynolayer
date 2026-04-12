import re

import boto3
import pytest
from dynolayer.dynolayer import DynoLayer
from dynolayer.exceptions import InvalidArgumentException, AutoIdException


# --- Fixtures ---

@pytest.fixture
def create_table_str_pk(aws_mock):
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName="products",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def create_table_num_pk(aws_mock):
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName="orders",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "N"}],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def create_sequences_table(aws_mock):
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName="dynolayer_sequences",
        KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def get_product_uuid4():
    class Product(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="products",
                required_fields=["name"],
                fillable=["id", "name", "price"],
                timestamps=False,
                auto_id="uuid4",
                partition_key="id",
            )
    return Product


@pytest.fixture
def get_product_uuid1():
    class Product(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="products",
                required_fields=["name"],
                fillable=["id", "name", "price"],
                timestamps=False,
                auto_id="uuid1",
                partition_key="id",
            )
    return Product


@pytest.fixture
def get_product_uuid4_truncated():
    class Product(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="products",
                required_fields=["name"],
                fillable=["id", "name", "price"],
                timestamps=False,
                auto_id="uuid4",
                auto_id_length=16,
                partition_key="id",
            )
    return Product


@pytest.fixture
def get_order_numeric():
    class Order(DynoLayer):
        def __init__(self):
            super().__init__(
                entity="orders",
                required_fields=["total"],
                fillable=["id", "total", "status"],
                timestamps=False,
                auto_id="numeric",
                partition_key="id",
            )
    return Order


# --- UUID4 Tests ---

class TestAutoIdUuid4:
    UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

    def test_create_generates_uuid4(self, get_product_uuid4, create_table_str_pk, aws_mock):
        product = get_product_uuid4.create({"name": "Widget"})
        assert product.id is not None
        assert self.UUID_PATTERN.match(product.id)

    def test_create_with_explicit_id_skips_generation(self, get_product_uuid4, create_table_str_pk, aws_mock):
        product = get_product_uuid4.create({"id": "my-custom-id", "name": "Widget"})
        assert product.id == "my-custom-id"

    def test_batch_create_generates_unique_ids(self, get_product_uuid4, create_table_str_pk, aws_mock):
        products = get_product_uuid4.batch_create([
            {"name": "Widget A"},
            {"name": "Widget B"},
            {"name": "Widget C"},
        ])
        ids = [p.id for p in products]
        assert len(set(ids)) == 3
        for pid in ids:
            assert self.UUID_PATTERN.match(pid)

    def test_save_generates_uuid4(self, get_product_uuid4, create_table_str_pk, aws_mock):
        product = get_product_uuid4()
        product.name = "Widget"
        product.save()
        assert product.id is not None
        assert self.UUID_PATTERN.match(product.id)

    def test_save_does_not_regenerate_on_update(self, get_product_uuid4, create_table_str_pk, aws_mock):
        product = get_product_uuid4.create({"name": "Widget"})
        original_id = product.id

        product.name = "Updated Widget"
        product.save()
        assert product.id == original_id

    def test_batch_create_mixed_explicit_and_auto(self, get_product_uuid4, create_table_str_pk, aws_mock):
        products = get_product_uuid4.batch_create([
            {"id": "explicit-id", "name": "Widget A"},
            {"name": "Widget B"},
        ])
        assert products[0].id == "explicit-id"
        assert self.UUID_PATTERN.match(products[1].id)


# --- UUID1 Tests ---

class TestAutoIdUuid1:
    UUID1_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

    def test_create_generates_uuid1(self, get_product_uuid1, create_table_str_pk, aws_mock):
        product = get_product_uuid1.create({"name": "Widget"})
        assert product.id is not None
        assert self.UUID1_PATTERN.match(product.id)


# --- UUID Length Tests ---

class TestAutoIdLength:
    def test_create_generates_truncated_uuid(self, get_product_uuid4_truncated, create_table_str_pk, aws_mock):
        product = get_product_uuid4_truncated.create({"name": "Widget"})
        assert product.id is not None
        assert len(product.id) == 16
        assert re.match(r"^[0-9a-f]{16}$", product.id)

    def test_batch_create_truncated_unique(self, get_product_uuid4_truncated, create_table_str_pk, aws_mock):
        products = get_product_uuid4_truncated.batch_create([
            {"name": "A"},
            {"name": "B"},
        ])
        assert len(products[0].id) == 16
        assert len(products[1].id) == 16
        assert products[0].id != products[1].id


# --- Numeric Tests ---

class TestAutoIdNumeric:
    def test_create_generates_sequential_ids(self, get_order_numeric, create_table_num_pk, create_sequences_table, aws_mock):
        order1 = get_order_numeric.create({"total": 100, "status": "pending"})
        order2 = get_order_numeric.create({"total": 200, "status": "pending"})
        order3 = get_order_numeric.create({"total": 300, "status": "pending"})

        assert order1.id == 1
        assert order2.id == 2
        assert order3.id == 3

    def test_batch_create_generates_sequential_ids(self, get_order_numeric, create_table_num_pk, create_sequences_table, aws_mock):
        orders = get_order_numeric.batch_create([
            {"total": 100, "status": "pending"},
            {"total": 200, "status": "pending"},
            {"total": 300, "status": "pending"},
        ])

        assert orders[0].id == 1
        assert orders[1].id == 2
        assert orders[2].id == 3

    def test_create_with_explicit_id_skips_generation(self, get_order_numeric, create_table_num_pk, create_sequences_table, aws_mock):
        order = get_order_numeric.create({"id": 999, "total": 100, "status": "pending"})
        assert order.id == 999

    def test_fails_when_sequences_table_missing(self, get_order_numeric, create_table_num_pk, aws_mock):
        with pytest.raises(AutoIdException, match="Sequences table"):
            get_order_numeric.create({"total": 100, "status": "pending"})

    def test_save_generates_numeric_id(self, get_order_numeric, create_table_num_pk, create_sequences_table, aws_mock):
        order = get_order_numeric()
        order.total = 100
        order.status = "pending"
        order.save()
        assert order.id == 1

    def test_batch_create_mixed_explicit_and_auto(self, get_order_numeric, create_table_num_pk, create_sequences_table, aws_mock):
        orders = get_order_numeric.batch_create([
            {"id": 999, "total": 100, "status": "pending"},
            {"total": 200, "status": "pending"},
            {"total": 300, "status": "pending"},
        ])
        assert orders[0].id == 999
        assert orders[1].id == 1
        assert orders[2].id == 2


# --- Validation Tests ---

class TestAutoIdValidation:
    def test_invalid_strategy_raises(self):
        with pytest.raises(InvalidArgumentException, match="Invalid auto_id strategy"):
            class Bad(DynoLayer):
                def __init__(self):
                    super().__init__(entity="t", partition_key="id", auto_id="invalid")
            Bad()

    def test_numeric_with_length_raises(self):
        with pytest.raises(InvalidArgumentException, match="not supported with 'numeric'"):
            class Bad(DynoLayer):
                def __init__(self):
                    super().__init__(entity="t", partition_key="id", auto_id="numeric", auto_id_length=16)
            Bad()

    def test_length_below_minimum_raises(self):
        with pytest.raises(InvalidArgumentException, match="between 16 and 32"):
            class Bad(DynoLayer):
                def __init__(self):
                    super().__init__(entity="t", partition_key="id", auto_id="uuid4", auto_id_length=8)
            Bad()

    def test_length_above_maximum_raises(self):
        with pytest.raises(InvalidArgumentException, match="between 16 and 32"):
            class Bad(DynoLayer):
                def __init__(self):
                    super().__init__(entity="t", partition_key="id", auto_id="uuid4", auto_id_length=40)
            Bad()


# --- Default behavior ---

class TestAutoIdDisabled:
    def test_no_auto_id_by_default(self, get_user, create_table, aws_mock, save_records):
        user = get_user.get_item({"id": 1})
        assert user is not None
        assert user.id == 1


if __name__ == "__main__":
    pytest.main()
