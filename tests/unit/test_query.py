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
def test_it_should_query_a_batch_of_records():
    create_table()
    save_record()
    user = User()
    response = user.query_by('role', 'admin', 'role-index').fetch(object=True)
    assert response
    assert len(response) == 2
    response_partition = user.query_by('id', '123456').fetch(object=True)
    assert response_partition
    assert len(response_partition) == 1


@mock_aws
def test_it_should_find_a_collection_of_records_by_filter():
    create_table()
    save_record()
    user = User()
    # adicionar propriedade com nome reservado pelo DynamoDB
    user.id = '123456'
    user.name = 'Messi'
    user.save()

    response = user.query(
        '#r = :r',
        {':r': 'common'},
        {'#r': 'role', '#name': 'name'},
        'role-index'
    ).attributes_to_get('last_name,stars,#name').fetch(object=True)
    assert user.get_count == 1
    assert 'first_name' not in response[0].data()
    assert response[0].data().get('last_name', None)
    assert response[0].data().get('stars', None)

    response_query_by = user.query_by(
        'id',
        '123456'
    ).attributes_to_get('last_name,stars,name').fetch(object=True)
    assert user.get_count == 1
    assert 'first_name' not in response_query_by[0].data()
    assert response_query_by[0].data().get('last_name', None)
    assert response_query_by[0].data().get('stars', None)


@mock_aws
def test_it_should_return_the_items_count():
    create_table()
    save_record()
    user = User()
    total_count = user.query_by('role', 'admin', 'role-index').count()
    assert total_count == 2


if __name__ == '__main__':
    pytest.main()
