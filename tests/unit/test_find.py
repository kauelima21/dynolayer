import boto3
import pytest
from dynolayer.dynolayer import DynoLayer
from moto import mock_aws


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
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'role',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        },
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'role-index',
                'KeySchema': [
                    {
                        'AttributeName': 'role',
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
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
            'role': 'admin',
            'stars': 5,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            'id': '567890',
            'first_name': 'Elton',
            'last_name': 'Moon',
            'role': 'common',
            'stars': 11,
        }
    )
    dynamodb.Table(table_name).put_item(
        Item={
            'id': '308789',
            'first_name': 'Anna',
            'last_name': 'Luh',
            'role': 'admin',
            'stars': 52,
        }
    )


class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__('users', [])


@mock_aws
def test_it_should_find_a_record_by_id():
    create_table()
    save_record()
    user = User()
    response = user.find_by_id('123456')
    data = response.data()
    assert response
    assert data.get('id') == '123456'


@mock_aws
def test_it_should_find_a_collection_of_records():
    create_table()
    save_record()
    user = User()
    response = user.find().limit(2).fetch()
    assert user.count == 2
    assert response


@mock_aws
def test_it_should_find_a_collection_of_records_by_filter():
    create_table()
    save_record()
    user = User()
    # adicionar propriedade com nome reservado pelo DynamoDB
    user.id = '123456'
    user.name = 'Messi'
    user.save()

    response = user.find(
        '#fn = :fn',
        {':fn': 'John'},
        {'#fn': 'first_name', '#name': 'name'}
    ).attributes_to_get('last_name,stars,#name').fetch()
    assert user.count == 1
    assert 'first_name' not in response[0]
    assert response[0].get('last_name', None)
    assert response[0].get('stars', None)

    response_find_by = user.find_by(
        'first_name',
        'John'
    ).attributes_to_get('last_name,stars,name').fetch()
    assert user.count == 1
    assert 'first_name' not in response_find_by[0]
    assert response_find_by[0].get('last_name', None)
    assert response_find_by[0].get('stars', None)


@mock_aws
def test_it_should_paginate():
    create_table()
    save_record()

    limit = 1
    user = User()

    user.find().fetch(True)
    total_count = user.count

    search = user.find().limit(limit)

    last_evaluated_key = {'id': '123456'}
    if last_evaluated_key:
        search = search.offset(last_evaluated_key)

    results = search.fetch()
    results_count = user.count

    assert total_count == 3
    assert results
    assert results_count == limit
    assert user.last_evaluated_key != {'id': '123456'}


@mock_aws
def test_it_should_fetch_records_ordered():
    create_table()
    save_record()
    user = User()
    response_ascending = user.find().order('first_name').fetch()
    assert response_ascending[0].get('first_name', None) == 'Anna'
    assert response_ascending[2].get('first_name', None) == 'John'
    response_descending = user.find().order('first_name', False).fetch()
    assert response_descending[0].get('first_name', None) == 'John'
    assert response_descending[2].get('first_name', None) == 'Anna'


if __name__ == '__main__':
    pytest.main()
