import boto3
import pytest
from src.dynolayer import DynoLayer
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
def test_it_should_find_a_record_by_id():
    create_table()
    save_record()
    user = User()
    response = user.find_by_id('123456')
    assert response


@mock_dynamodb
def test_it_should_find_a_collection_of_records():
    create_table()
    save_record()
    user = User()
    response = user.find().limit(2).fetch()
    assert len(response) == 2


@mock_dynamodb
def test_it_should_find_a_collection_of_records_by_filter():
    create_table()
    save_record()
    user = User()
    response = user.find(
        '#fn = :fn',
        {':fn': 'John'},
        {'#fn': 'first_name'}
    ).attributes_to_get('last_name,stars').fetch()
    assert len(response) == 1
    assert 'first_name' not in response[0]


if __name__ == '__main__':
    pytest.main()
