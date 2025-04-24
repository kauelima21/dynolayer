import boto3
import pytest
from faker import Faker
from moto import mock_aws

from dynolayer.dynolayer import DynoLayer


@pytest.fixture
def get_user():
    class User(DynoLayer):
        def __init__(self) -> None:
            super().__init__(
                entity="users",
                required_fields=["first_name", "email", "role"],
                fillable=["id", "first_name", "last_name", "email", "role", "stars", "stats", "phones"],
                timestamps=True
            )

    return User


@pytest.fixture()
def faker():
    yield Faker(['en_US', 'pt_BR'])


@pytest.fixture(scope="function")
def aws_mock():
    with mock_aws():
        yield


@pytest.fixture
def create_table(aws_mock):
    table_name = "users"
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "N"},
                              {"AttributeName": "role", "AttributeType": "S"},
                              {"AttributeName": "email", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "role-index",
                "KeySchema": [{"AttributeName": "role", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "role-email-index",
                "KeySchema": [{"AttributeName": "role", "KeyType": "HASH"},
                              {"AttributeName": "email", "KeyType": "RANGE"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )


@pytest.fixture(scope="function")
def save_records(faker, aws_mock):
    from datetime import datetime, timedelta, timezone

    table_name = "users"
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")

    for i in range(20):
        mock_item = {
            "id": i + 1,
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "stars": faker.random_int(min=0, max=5),
            "role": faker.random_element(elements=["admin", "common", "moderator"]),
            "created_at": int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp()),
            "updated_at": int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp()),
        }
        dynamodb.Table(table_name).put_item(Item=mock_item)
