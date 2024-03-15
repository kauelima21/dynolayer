import boto3
import pytest
from dynolayer.dynolayer import DynoLayer
from moto import mock_dynamodb


def create_table():
    table_name = 'users'
    dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions= [
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput= {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    return response


def save_record():
    table_name = 'users'
    dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
    dynamodb.Table(table_name).put_item(
        Item={
            'id': '123456',
            'first_name': 'John',
            'last_name': 'Doe',
            'stars': 5,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            'id': '567890',
            'first_name': 'Elton',
            'last_name': 'Moon',
            'stars': 11,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            'id': '308789',
            'first_name': 'Anna',
            'last_name': 'Luh',
            'stars': 52,
        }
    )


class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__('users', [])


@mock_dynamodb
def test_it_should_destroy_a_record():
    create_table()
    save_record()
    user = User().find_by_id('123456')
    assert len(user.find().fetch()) == 3
    assert user.destroy()
    assert len(user.find().fetch()) == 2


if __name__ == '__main__':
    pytest.main()
