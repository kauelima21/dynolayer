import os

import boto3
import pytest
from moto import mock_aws

from dynolayer.dynolayer import DynoLayer


def create_table():
    table_name = "users"
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
    return response


def save_record():
    table_name = "users"
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    dynamodb.Table(table_name).put_item(
        Item={
            "id": "123456",
            "first_name": "John",
            "last_name": "Doe",
            "stars": 5,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            "id": "567890",
            "first_name": "Elton",
            "last_name": "Moon",
            "stars": 11,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            "id": "308789",
            "first_name": "Anna",
            "last_name": "Luh",
            "stars": 52,
        }
    )


class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__("users", ["first_name"])


@mock_aws
def test_it_should_create_a_record():
    create_table()
    user = User()
    user.first_name = "John"
    user.last_name = "Doe"
    user.email = "john@mail.com"
    user.stars = 5
    user.stats = {
        "wins": 32,
        "loss": 7,
    }
    user.phones = [
        "11 91234-5678",
        "10 95678-1234",
    ]
    os.environ["TIMESTAMP_TIMEZONE"] = "US/Pacific"
    assert user.save()
    assert user.id


@mock_aws
def test_it_should_not_create_a_record():
    create_table()
    user = User()
    user.last_name = "Doe"
    user.email = "john@mail.com"
    user.stars = 5
    user.stats = {
        "wins": 32,
        "loss": 7,
    }
    user.phones = [
        "11 91234-5678",
        "10 95678-1234",
    ]
    assert not user.save()
    assert user.error == "All required fields must be setted"


@mock_aws
def test_it_should_update_a_record():
    create_table()
    save_record()
    user = User().find_by_id("123456")
    user.first_name = "Messi"
    assert user.save()


if __name__ == "__main__":
    pytest.main()
